#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATE_KEY="${1:-$(TZ=Asia/Seoul date +%F)}"

# Validate DATE_KEY format to prevent path traversal
if ! [[ "$DATE_KEY" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "Invalid DATE_KEY format: $DATE_KEY (expected YYYY-MM-DD)" >&2
  exit 1
fi
PROMPT_FILE="$ROOT_DIR/prompts/openclaw_collection_brief.md"
OUTPUT_FILE="$ROOT_DIR/data/raw/openclaw_${DATE_KEY}.jsonl"
META_FILE="$ROOT_DIR/logs/openclaw_${DATE_KEY}.log"
RUNNER_DIAG_FILE="$ROOT_DIR/logs/openclaw_${DATE_KEY}.diag.jsonl"
COLLECTION_DIAG_FILE="$ROOT_DIR/logs/openclaw_${DATE_KEY}.collection.jsonl"
FALLBACK_MARKER="$ROOT_DIR/data/raw/openclaw_${DATE_KEY}.fallback_from"
COLLECTION_NEEDED_MARKER="$ROOT_DIR/data/raw/.collection_needed_${DATE_KEY}"
ADAPTIVE_POLICY_FILE="$ROOT_DIR/logs/openclaw_adaptive_policy.env"

MIN_RECORDS="${MIN_RECORDS:-200}"
MIN_COUNTRIES="${MIN_COUNTRIES:-16}"
MAX_COLLECTION_STALENESS_DAYS="${MAX_COLLECTION_STALENESS_DAYS:-21}"
ENABLE_OPENCLAW_LAST_SUCCESS_FALLBACK="${ENABLE_OPENCLAW_LAST_SUCCESS_FALLBACK:-1}"
OPENCLAW_ADAPTIVE_POLICY_MAX_LEVEL="${OPENCLAW_ADAPTIVE_POLICY_MAX_LEVEL:-3}"

mkdir -p "$ROOT_DIR/data/raw" "$ROOT_DIR/logs"
rm -f "$FALLBACK_MARKER" "$COLLECTION_NEEDED_MARKER"
: > "$COLLECTION_DIAG_FILE"

echo "[openclaw] date=$DATE_KEY" | tee "$META_FILE"
echo "[openclaw] prompt=$PROMPT_FILE" | tee -a "$META_FILE"

diag_event() {
  local stage="$1"
  local status="$2"
  local reason="$3"
  local extra="${4-}"
  if [[ -z "$extra" ]]; then
    extra="{}"
  fi
  jq -nc \
    --arg ts "$(TZ=Asia/Seoul date +%FT%T%z)" \
    --arg stage "$stage" \
    --arg status "$status" \
    --arg reason "$reason" \
    --argjson extra "$extra" \
    '{ts:$ts,stage:$stage,status:$status,reason:$reason,extra:$extra}' \
    >> "$COLLECTION_DIAG_FILE"
}

is_recent_enough() {
  local target="$1"
  python3 - <<PY
import datetime
today = datetime.date.fromisoformat("${DATE_KEY}")
target = datetime.date.fromisoformat("${target}")
max_days = int("${MAX_COLLECTION_STALENESS_DAYS}")
print("1" if (today - target).days <= max_days else "0")
PY
}

is_quality_raw() {
  local f="$1"
  [[ -f "$f" ]] || return 1

  local records countries
  records=$(wc -l < "$f" | tr -d ' ')
  countries=$(jq -r '.country // empty' "$f" 2>/dev/null | sort -u | wc -l | tr -d ' ')

  if [[ "$records" -lt "$MIN_RECORDS" ]] || [[ "$countries" -lt "$MIN_COUNTRIES" ]]; then
    return 1
  fi
  if rg -q '"signal_type":"collection_failed"|placeholder' "$f"; then
    return 1
  fi
  return 0
}

find_latest_success_raw() {
  shopt -s nullglob
  local files=("$ROOT_DIR"/data/raw/openclaw_*.jsonl)
  shopt -u nullglob
  [[ "${#files[@]}" -gt 0 ]] || return 1

  local sorted
  sorted=$(printf '%s\n' "${files[@]}" | sort -r)
  while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    local base d
    base="$(basename "$f")"
    d="${base#openclaw_}"
    d="${d%.jsonl}"
    [[ "$d" == "$DATE_KEY" ]] && continue
    [[ "$d" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || continue
    [[ "$(is_recent_enough "$d")" == "1" ]] || continue
    if is_quality_raw "$f"; then
      echo "$f"
      return 0
    fi
  done <<< "$sorted"
  return 1
}

runner_attempts_from_slice() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo 0
    return
  fi
  jq -r 'select(.event=="attempt_result") | 1' "$f" 2>/dev/null | wc -l | tr -d ' '
}

runner_top_reason_from_slice() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo "unknown"
    return
  fi
  local reason
  reason=$(jq -r 'select(.event=="attempt_result") | .reason // empty' "$f" 2>/dev/null | sort | uniq -c | sort -rn | awk 'NR==1{print $2}')
  echo "${reason:-unknown}"
}

runner_total_ms_from_slice() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo 0
    return
  fi
  local total
  total=$(jq -r 'select(.event=="run_summary") | .total_elapsed_ms // 0' "$f" 2>/dev/null | tail -n 1)
  echo "${total:-0}"
}

runner_status_from_slice() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo "unknown"
    return
  fi
  local status
  status=$(jq -r 'select(.event=="run_summary") | .status // empty' "$f" 2>/dev/null | tail -n 1)
  echo "${status:-unknown}"
}

is_number() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

max_int() {
  local a="$1"
  local b="$2"
  if [[ "$a" -ge "$b" ]]; then
    echo "$a"
  else
    echo "$b"
  fi
}

apply_if_lower() {
  local var_name="$1"
  local recommended="$2"
  local current="${!var_name:-0}"
  if ! is_number "$current"; then
    current=0
  fi
  if [[ "$current" -lt "$recommended" ]]; then
    export "$var_name=$recommended"
  fi
}

POLICY_LAST_REASON="none"
POLICY_LEVEL=0

load_adaptive_policy() {
  if [[ -f "$ADAPTIVE_POLICY_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$ADAPTIVE_POLICY_FILE"
    POLICY_LAST_REASON="${LAST_REASON:-none}"
    POLICY_LEVEL="${LEVEL:-0}"
  fi

  if ! is_number "$POLICY_LEVEL"; then
    POLICY_LEVEL=0
  fi

  if [[ "$POLICY_LEVEL" -gt 0 ]] && [[ "$POLICY_LAST_REASON" =~ ^(timeout|rate_limited|session_lock)$ ]]; then
    local level retries base cap rate_extra lock_extra
    level="$POLICY_LEVEL"
    retries=$((3 + level))
    base=$((10 + (5 * level)))
    cap=$((180 + (60 * level)))
    rate_extra=$((25 + (10 * level)))
    lock_extra=$((15 + (5 * level)))

    apply_if_lower "OPENCLAW_MAX_RETRIES" "$retries"
    apply_if_lower "OPENCLAW_BACKOFF_BASE_SECONDS" "$base"
    apply_if_lower "OPENCLAW_BACKOFF_CAP_SECONDS" "$cap"
    apply_if_lower "OPENCLAW_RATE_LIMIT_EXTRA_SECONDS" "$rate_extra"
    apply_if_lower "OPENCLAW_SESSION_LOCK_EXTRA_SECONDS" "$lock_extra"

    echo "[openclaw] adaptive policy applied: reason=$POLICY_LAST_REASON level=$POLICY_LEVEL retries=${OPENCLAW_MAX_RETRIES:-$retries} base=${OPENCLAW_BACKOFF_BASE_SECONDS:-$base}" | tee -a "$META_FILE"
    diag_event "adaptive_policy" "applied" "$POLICY_LAST_REASON" "{\"level\":$POLICY_LEVEL,\"retries\":${OPENCLAW_MAX_RETRIES:-$retries},\"base_backoff\":${OPENCLAW_BACKOFF_BASE_SECONDS:-$base}}"
  else
    diag_event "adaptive_policy" "skipped" "$POLICY_LAST_REASON" "{\"level\":$POLICY_LEVEL}"
  fi
}

save_adaptive_policy() {
  local new_reason="$1"
  local success="$2"
  local new_level

  if [[ "$success" == "1" ]]; then
    new_level=0
    new_reason="success"
  elif [[ "$new_reason" =~ ^(timeout|rate_limited|session_lock)$ ]]; then
    if [[ "$new_reason" == "$POLICY_LAST_REASON" ]] && [[ "$POLICY_LEVEL" -gt 0 ]]; then
      new_level=$((POLICY_LEVEL + 1))
    else
      new_level=1
    fi
    if [[ "$new_level" -gt "$OPENCLAW_ADAPTIVE_POLICY_MAX_LEVEL" ]]; then
      new_level="$OPENCLAW_ADAPTIVE_POLICY_MAX_LEVEL"
    fi
  else
    new_level=0
  fi

  cat > "$ADAPTIVE_POLICY_FILE" <<EOF
LAST_REASON=$new_reason
LEVEL=$new_level
UPDATED_DATE=$DATE_KEY
EOF

  echo "[openclaw] adaptive policy saved: reason=$new_reason level=$new_level" | tee -a "$META_FILE"
  diag_event "adaptive_policy" "saved" "$new_reason" "{\"level\":$new_level}"
}

load_adaptive_policy

runner_diag_start=0
if [[ -f "$RUNNER_DIAG_FILE" ]]; then
  runner_diag_start=$(wc -l < "$RUNNER_DIAG_FILE" | tr -d ' ')
fi

collection_success=false
primary_failure_reason="unknown"
runner_slice_file="$ROOT_DIR/logs/openclaw_${DATE_KEY}.diag.current.jsonl"
rm -f "$runner_slice_file"

# Primary: OpenClaw runner
if [[ -n "${OPENCLAW_RUNNER:-}" ]]; then
  echo "[openclaw] PRIMARY: running external runner" | tee -a "$META_FILE"
  diag_event "primary" "start" "runner_start" "{\"runner\":$(jq -Rn --arg v "$OPENCLAW_RUNNER" '$v')}"

  if "$OPENCLAW_RUNNER" "$PROMPT_FILE" "$OUTPUT_FILE" "$META_FILE"; then
    :
  else
    rc=$?
    echo "[openclaw] PRIMARY: runner failed (rc=$rc)" | tee -a "$META_FILE"
  fi

  if [[ -f "$RUNNER_DIAG_FILE" ]]; then
    total_lines=$(wc -l < "$RUNNER_DIAG_FILE" | tr -d ' ')
    if [[ "$total_lines" -gt "$runner_diag_start" ]]; then
      tail -n "+$((runner_diag_start + 1))" "$RUNNER_DIAG_FILE" > "$runner_slice_file"
    fi
  fi

  runner_attempts="$(runner_attempts_from_slice "$runner_slice_file")"
  runner_top_reason="$(runner_top_reason_from_slice "$runner_slice_file")"
  runner_total_ms="$(runner_total_ms_from_slice "$runner_slice_file")"
  runner_status="$(runner_status_from_slice "$runner_slice_file")"

  if is_quality_raw "$OUTPUT_FILE"; then
    echo "[openclaw] PRIMARY: quality pass" | tee -a "$META_FILE"
    diag_event "primary" "success" "quality_pass" "{\"attempts\":$runner_attempts,\"top_reason\":$(jq -Rn --arg v "$runner_top_reason" '$v'),\"runner_status\":$(jq -Rn --arg v "$runner_status" '$v'),\"total_ms\":$runner_total_ms}"
    collection_success=true
  else
    primary_failure_reason="$runner_top_reason"
    if [[ "$primary_failure_reason" == "unknown" ]] || [[ "$primary_failure_reason" == "success" ]]; then
      primary_failure_reason="quality_below_threshold"
    fi
    echo "[openclaw] PRIMARY: output exists but quality below threshold (records/countries)" | tee -a "$META_FILE"
    diag_event "primary" "failed" "$primary_failure_reason" "{\"attempts\":$runner_attempts,\"runner_status\":$(jq -Rn --arg v "$runner_status" '$v'),\"total_ms\":$runner_total_ms}"
  fi
else
  primary_failure_reason="runner_not_configured"
  echo "[openclaw] PRIMARY: OPENCLAW_RUNNER is not set" | tee -a "$META_FILE"
  diag_event "primary" "failed" "$primary_failure_reason" "{}"
fi

# Fallback 1: fresh collection via Brave Search + Scrapling enrichment
if [[ "$collection_success" != "true" ]] && [[ "${ENABLE_BRAVE_SEARCH_FALLBACK:-1}" == "1" ]]; then
  echo "[openclaw] FALLBACK1: running Brave Search + Scrapling collector" | tee -a "$META_FILE"
  diag_event "fallback1" "start" "brave_scrapling_start" "{}"
  if [[ -n "${BRAVE_API_KEY:-}" ]]; then
    if python3 "$ROOT_DIR/scripts/d2c_search.py" "$DATE_KEY" >> "$META_FILE" 2>&1; then
      if is_quality_raw "$OUTPUT_FILE"; then
        echo "[openclaw] FALLBACK1: fresh collection quality pass" | tee -a "$META_FILE"
        diag_event "fallback1" "success" "brave_scrapling_quality_pass" "{\"output\":$(jq -Rn --arg v "$OUTPUT_FILE" '$v')}"
        collection_success=true
      else
        echo "[openclaw] FALLBACK1: collector completed but quality below threshold" | tee -a "$META_FILE"
        diag_event "fallback1" "failed" "brave_scrapling_quality_below_threshold" "{}"
      fi
    else
      echo "[openclaw] FALLBACK1: collector execution failed" | tee -a "$META_FILE"
      diag_event "fallback1" "failed" "brave_scrapling_execution_failed" "{}"
    fi
  else
    echo "[openclaw] FALLBACK1: BRAVE_API_KEY is not set" | tee -a "$META_FILE"
    diag_event "fallback1" "failed" "brave_api_key_missing" "{}"
  fi
fi

# Fallback 2: latest successful raw reuse
if [[ "$collection_success" != "true" ]] && [[ "$ENABLE_OPENCLAW_LAST_SUCCESS_FALLBACK" == "1" ]]; then
  echo "[openclaw] FALLBACK2: searching latest successful raw (<=${MAX_COLLECTION_STALENESS_DAYS}d)" | tee -a "$META_FILE"
  if latest_raw="$(find_latest_success_raw)"; then
    cp "$latest_raw" "$OUTPUT_FILE"
    latest_date="$(basename "$latest_raw" | sed -E 's/^openclaw_([0-9]{4}-[0-9]{2}-[0-9]{2})\.jsonl$/\1/')"
    echo "$latest_date" > "$FALLBACK_MARKER"
    echo "[openclaw] FALLBACK2: reused raw from $latest_date" | tee -a "$META_FILE"
    diag_event "fallback2" "success" "reuse_latest_success" "{\"source_date\":$(jq -Rn --arg v "$latest_date" '$v')}"
    collection_success=true
  else
    echo "[openclaw] FALLBACK2: no reusable raw found" | tee -a "$META_FILE"
    diag_event "fallback2" "failed" "no_reusable_raw" "{}"
  fi
fi

# Fallback 3: async recovery marker
if [[ "$collection_success" != "true" ]]; then
  echo "$DATE_KEY" > "$COLLECTION_NEEDED_MARKER"
  echo "[openclaw] FALLBACK3: recovery marker created ($COLLECTION_NEEDED_MARKER)" | tee -a "$META_FILE"
  diag_event "fallback3" "created" "collection_needed_marker" "{\"marker\":$(jq -Rn --arg v "$COLLECTION_NEEDED_MARKER" '$v')}"
fi

if [[ "$collection_success" == "true" ]]; then
  save_adaptive_policy "success" "1"
  echo "[openclaw] output=$OUTPUT_FILE ($(wc -l < "$OUTPUT_FILE" | tr -d ' ') records)" | tee -a "$META_FILE"
  diag_event "final" "success" "collection_ready" "{\"output\":$(jq -Rn --arg v "$OUTPUT_FILE" '$v')}"
  rm -f "$runner_slice_file"
  exit 0
fi

save_adaptive_policy "$primary_failure_reason" "0"

# Debug-only placeholder guard (disabled by default)
if [[ "${ALLOW_OPENCLAW_PLACEHOLDER:-0}" == "1" ]]; then
  echo "[openclaw] DEBUG: writing placeholder record" | tee -a "$META_FILE"
  jq -nc --arg ts "$(TZ=Asia/Seoul date +%FT%T%z)" \
    '{country:"GLOBAL",product:"UNKNOWN",pillar:"Collection",brand:"UNKNOWN",signal_type:"collection_failed",value:"Placeholder due collection failure",currency:"",quote_original:"",source_url:"",collected_at:$ts,confidence:0.1}' \
    > "$OUTPUT_FILE"
  echo "[openclaw] output=$OUTPUT_FILE (debug placeholder)" | tee -a "$META_FILE"
  diag_event "final" "success" "debug_placeholder" "{}"
  rm -f "$runner_slice_file"
  exit 0
fi

echo "[openclaw] collection failed and no safe fallback available" | tee -a "$META_FILE"
diag_event "final" "failed" "$primary_failure_reason" "{}"
rm -f "$runner_slice_file"
exit 1
