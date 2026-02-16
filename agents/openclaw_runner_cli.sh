#!/usr/bin/env bash
set -euo pipefail

PROMPT_FILE="$1"
OUTPUT_FILE="$2"
META_FILE="$3"

OPENCLAW_AGENT_ID="${OPENCLAW_AGENT_ID:-main}"
OPENCLAW_ALT_AGENT_IDS="${OPENCLAW_ALT_AGENT_IDS:-}"
OPENCLAW_TIMEOUT_SECONDS="${OPENCLAW_TIMEOUT_SECONDS:-600}"
OPENCLAW_MAX_RETRIES="${OPENCLAW_MAX_RETRIES:-${MAX_RETRIES:-3}}"
OPENCLAW_BACKOFF_BASE_SECONDS="${OPENCLAW_BACKOFF_BASE_SECONDS:-10}"
OPENCLAW_BACKOFF_MULTIPLIER="${OPENCLAW_BACKOFF_MULTIPLIER:-2}"
OPENCLAW_BACKOFF_CAP_SECONDS="${OPENCLAW_BACKOFF_CAP_SECONDS:-180}"
OPENCLAW_JITTER_MAX_SECONDS="${OPENCLAW_JITTER_MAX_SECONDS:-7}"
OPENCLAW_RATE_LIMIT_EXTRA_SECONDS="${OPENCLAW_RATE_LIMIT_EXTRA_SECONDS:-25}"
OPENCLAW_SESSION_LOCK_EXTRA_SECONDS="${OPENCLAW_SESSION_LOCK_EXTRA_SECONDS:-15}"
OPENCLAW_ENABLE_STALE_LOCK_CLEANUP="${OPENCLAW_ENABLE_STALE_LOCK_CLEANUP:-1}"
OPENCLAW_AUTO_ADD_MAIN_AGENT="${OPENCLAW_AUTO_ADD_MAIN_AGENT:-1}"

MIN_RECORDS="${MIN_RECORDS:-200}"
MIN_COUNTRIES="${MIN_COUNTRIES:-16}"
MIN_FRIDGE="${MIN_FRIDGE:-40}"
MIN_WASHER="${MIN_WASHER:-35}"
MIN_MONITOR="${MIN_MONITOR:-15}"
MIN_GRAM="${MIN_GRAM:-10}"
MAX_TV_RATIO="${MAX_TV_RATIO:-45}"

TMP_DIR="$(mktemp -d)"
DIAG_FILE="${META_FILE%.log}.diag.jsonl"
REASONS_FILE="$TMP_DIR/reasons.log"
PROMPT_TEXT="$(cat "$PROMPT_FILE")"
LAST_REASON=""
LAST_BACKOFF_SECONDS=0

trap 'rm -rf "$TMP_DIR"' EXIT

AGENT_POOL=()

trim_spaces() {
  local raw="$1"
  raw="${raw#"${raw%%[![:space:]]*}"}"
  raw="${raw%"${raw##*[![:space:]]}"}"
  printf '%s' "$raw"
}

agent_exists_in_pool() {
  local target="$1"
  local current
  for current in "${AGENT_POOL[@]}"; do
    if [[ "$current" == "$target" ]]; then
      return 0
    fi
  done
  return 1
}

build_agent_pool() {
  local alt raw cleaned
  AGENT_POOL=()
  AGENT_POOL+=("$OPENCLAW_AGENT_ID")

  IFS=',' read -r -a alt <<< "$OPENCLAW_ALT_AGENT_IDS"
  for raw in "${alt[@]}"; do
    cleaned="$(trim_spaces "$raw")"
    [[ -z "$cleaned" ]] && continue
    if ! agent_exists_in_pool "$cleaned"; then
      AGENT_POOL+=("$cleaned")
    fi
  done

  if [[ "$OPENCLAW_AUTO_ADD_MAIN_AGENT" == "1" ]] && ! agent_exists_in_pool "main"; then
    AGENT_POOL+=("main")
  fi
}

agent_for_attempt() {
  local attempt="$1"
  local pool_size idx
  pool_size="${#AGENT_POOL[@]}"
  if [[ "$pool_size" -le 0 ]]; then
    printf '%s' "$OPENCLAW_AGENT_ID"
    return
  fi
  idx=$(( (attempt - 1) % pool_size ))
  printf '%s' "${AGENT_POOL[$idx]}"
}

now_ms() {
  python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
}

json_escape_string() {
  python3 - "$1" <<'PY'
import json
import sys
print(json.dumps(sys.argv[1]))
PY
}

log_diag_event() {
  local event="$1"
  local payload="$2"
  local timestamp
  timestamp="$(TZ=Asia/Seoul date +%FT%T%z)"
  echo "{\"event\":\"$event\",\"ts\":\"$timestamp\",${payload}}" >> "$DIAG_FILE"
}

extract_jsonl() {
  local source="$1"
  local dest="$2"
  local extracted

  if echo "$source" | jq -e 'type == "array"' >/dev/null 2>&1; then
    echo "$source" | jq -c '.[]' > "$dest"
    return 0
  fi

  if echo "$source" | jq -e 'type == "object"' >/dev/null 2>&1; then
    echo "$source" | jq -c '.' > "$dest"
    return 0
  fi

  extracted=$(echo "$source" | grep -E '^\s*\{' | while IFS= read -r line; do
    echo "$line" | jq -c '.' 2>/dev/null
  done || true)

  if [[ -n "$extracted" ]]; then
    echo "$extracted" > "$dest"
    return 0
  fi
  return 1
}

validate_quality() {
  local file="$1"
  local record_count country_count
  local tv_count fridge_count washer_count monitor_count gram_count
  local tv_ratio_pct low_conf_count low_conf_pct

  record_count=$(wc -l < "$file" | tr -d ' ')
  country_count=$(jq -r '.country // empty' "$file" 2>/dev/null | sort -u | wc -l | tr -d ' ')
  tv_count=$(jq -r 'select(.product=="TV") | 1' "$file" 2>/dev/null | wc -l | tr -d ' ')
  fridge_count=$(jq -r 'select(.product=="Refrigerator") | 1' "$file" 2>/dev/null | wc -l | tr -d ' ')
  washer_count=$(jq -r 'select(.product=="Washing Machine") | 1' "$file" 2>/dev/null | wc -l | tr -d ' ')
  monitor_count=$(jq -r 'select(.product=="Monitor") | 1' "$file" 2>/dev/null | wc -l | tr -d ' ')
  gram_count=$(jq -r 'select(.product=="LG gram") | 1' "$file" 2>/dev/null | wc -l | tr -d ' ')

  tv_ratio_pct=$(awk -v tv="$tv_count" -v total="$record_count" 'BEGIN{ if(total==0){print 0}else{printf "%.1f", (tv*100)/total} }')

  low_conf_count=$(jq -r '.confidence // empty' "$file" 2>/dev/null | grep -Eci "^(low|0(\.[0-4])?)$" || true)
  low_conf_pct=$((low_conf_count * 100 / (record_count > 0 ? record_count : 1)))

  {
    echo "[quality] records=$record_count countries=$country_count (min: records=$MIN_RECORDS countries=$MIN_COUNTRIES)"
    echo "[quality] products: TV=$tv_count Fridge=$fridge_count Washer=$washer_count Monitor=$monitor_count gram=$gram_count"
    echo "[quality] tv_ratio=${tv_ratio_pct}% (max: ${MAX_TV_RATIO}%)"
    echo "[quality] confidence: low=$low_conf_count (${low_conf_pct}%) — warning threshold: 20%"
    if [[ "$low_conf_pct" -gt 20 ]]; then
      echo "[quality] ⚠️ WARNING: low confidence ratio exceeds 20% — data quality risk"
    fi
  } >> "$META_FILE"

  if [[ "$record_count" -ge "$MIN_RECORDS" ]] \
    && [[ "$country_count" -ge "$MIN_COUNTRIES" ]] \
    && [[ "$fridge_count" -ge "$MIN_FRIDGE" ]] \
    && [[ "$washer_count" -ge "$MIN_WASHER" ]] \
    && [[ "$monitor_count" -ge "$MIN_MONITOR" ]] \
    && [[ "$gram_count" -ge "$MIN_GRAM" ]] \
    && awk -v r="$tv_ratio_pct" -v max="$MAX_TV_RATIO" 'BEGIN{exit !(r<=max)}'
  then
    return 0
  fi
  return 1
}

classify_failure_reason() {
  local rc="$1"
  local stderr_file="$2"
  local default_reason="$3"
  local stderr_text

  stderr_text="$(cat "$stderr_file" 2>/dev/null || true)"

  if echo "$stderr_text" | rg -qi "session file locked|FailoverError: session file locked"; then
    printf '%s' "session_lock"
    return
  fi
  if echo "$stderr_text" | rg -qi "RATE_LIMITED|status\":429|Request rate limit exceeded|rate limit"; then
    printf '%s' "rate_limited"
    return
  fi
  if [[ "$rc" == "124" ]] || echo "$stderr_text" | rg -qi "timed out|timeout"; then
    printf '%s' "timeout"
    return
  fi
  if [[ -n "$default_reason" ]]; then
    printf '%s' "$default_reason"
    return
  fi
  printf '%s' "command_failed"
}

cleanup_stale_lock_if_safe() {
  local stderr_file="$1"
  local parsed pid lock_path
  local allowed_prefix="$HOME/.openclaw/agents/"

  [[ "$OPENCLAW_ENABLE_STALE_LOCK_CLEANUP" == "1" ]] || return 0

  parsed="$(python3 - "$stderr_file" <<'PY'
import re
import sys
text = open(sys.argv[1], "r", encoding="utf-8", errors="ignore").read()
m = re.search(r"session file locked \(timeout \d+ms\): pid=(\d+)\s+([^\s]+\.lock)", text)
if m:
    print(m.group(1))
    print(m.group(2))
PY
)"

  [[ -n "$parsed" ]] || return 0
  pid="$(printf '%s\n' "$parsed" | sed -n '1p')"
  lock_path="$(printf '%s\n' "$parsed" | sed -n '2p')"
  [[ -n "$pid" && -n "$lock_path" ]] || return 0

  if [[ "$lock_path" != "$allowed_prefix"* ]]; then
    echo "[openclaw-cli] stale_lock_cleanup skipped: out-of-scope path ($lock_path)" >> "$META_FILE"
    return 0
  fi

  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "[openclaw-cli] stale_lock_cleanup skipped: owner pid alive ($pid)" >> "$META_FILE"
    return 0
  fi

  if [[ -f "$lock_path" ]]; then
    rm -f "$lock_path"
    echo "[openclaw-cli] stale_lock_cleanup removed stale lock: $lock_path (dead pid=$pid)" >> "$META_FILE"
  fi
}

pow_int() {
  local base="$1"
  local exp="$2"
  local value=1
  local i=0
  while [[ "$i" -lt "$exp" ]]; do
    value=$((value * base))
    i=$((i + 1))
  done
  printf '%s' "$value"
}

compute_backoff_seconds() {
  local attempt="$1"
  local reason="$2"
  local factor wait jitter

  factor="$(pow_int "$OPENCLAW_BACKOFF_MULTIPLIER" $((attempt - 1)))"
  wait=$((OPENCLAW_BACKOFF_BASE_SECONDS * factor))

  if [[ "$reason" == "rate_limited" ]]; then
    wait=$((wait + OPENCLAW_RATE_LIMIT_EXTRA_SECONDS))
  elif [[ "$reason" == "session_lock" ]]; then
    wait=$((wait + OPENCLAW_SESSION_LOCK_EXTRA_SECONDS))
  fi

  if [[ "$OPENCLAW_JITTER_MAX_SECONDS" -gt 0 ]]; then
    jitter=$((RANDOM % (OPENCLAW_JITTER_MAX_SECONDS + 1)))
    wait=$((wait + jitter))
  fi

  if [[ "$wait" -gt "$OPENCLAW_BACKOFF_CAP_SECONDS" ]]; then
    wait="$OPENCLAW_BACKOFF_CAP_SECONDS"
  fi
  printf '%s' "$wait"
}

record_attempt_result() {
  local attempt="$1"
  local agent="$2"
  local session_id="$3"
  local reason="$4"
  local rc="$5"
  local duration_ms="$6"
  local records="$7"
  local payload_status="$8"
  local backoff_seconds="$9"

  echo "$reason" >> "$REASONS_FILE"
  echo "[openclaw-cli] attempt_result attempt=$attempt agent=$agent reason=$reason rc=$rc duration_ms=$duration_ms records=$records payload=$payload_status backoff_s=$backoff_seconds session_id=$session_id" >> "$META_FILE"

  log_diag_event "attempt_result" "\"attempt\":$attempt,\"agent\":$(json_escape_string "$agent"),\"session_id\":$(json_escape_string "$session_id"),\"reason\":$(json_escape_string "$reason"),\"rc\":$rc,\"duration_ms\":$duration_ms,\"records\":$records,\"payload_status\":$(json_escape_string "$payload_status"),\"backoff_seconds\":$backoff_seconds"
}

run_collection() {
  local attempt="$1"
  local agent_id session_id tmp_json tmp_err payload_text lines reason
  local rc elapsed_ms start_ms end_ms backoff_seconds payload_status

  agent_id="$(agent_for_attempt "$attempt")"
  session_id="$(uuidgen | tr 'A-Z' 'a-z')"
  tmp_json="$TMP_DIR/attempt_${attempt}.json"
  tmp_err="$TMP_DIR/attempt_${attempt}.err"
  payload_status="none"
  lines=0

  {
    echo "[openclaw-cli] attempt=$attempt agent=$agent_id"
    echo "[openclaw-cli] timeout=${OPENCLAW_TIMEOUT_SECONDS}s session_id=$session_id"
  } >> "$META_FILE"

  start_ms="$(now_ms)"
  if perl -e 'my $t=shift @ARGV; local $SIG{ALRM}=sub{exit 124}; alarm $t; my $rc=system @ARGV; alarm 0; exit($rc == -1 ? 125 : ($rc >> 8));' "$OPENCLAW_TIMEOUT_SECONDS" \
      openclaw agent --agent "$agent_id" --session-id "$session_id" --local --json --timeout "$OPENCLAW_TIMEOUT_SECONDS" --message "$PROMPT_TEXT" \
      > "$tmp_json" 2> "$tmp_err"; then
    rc=0
  else
    rc=$?
  fi
  end_ms="$(now_ms)"
  elapsed_ms=$((end_ms - start_ms))

  if [[ -s "$tmp_err" ]]; then
    {
      echo "[openclaw-cli] attempt=$attempt stderr_begin"
      cat "$tmp_err"
      echo "[openclaw-cli] attempt=$attempt stderr_end"
    } >> "$META_FILE"
  fi

  if [[ "$rc" -ne 0 ]]; then
    reason="$(classify_failure_reason "$rc" "$tmp_err" "")"
    [[ "$reason" == "session_lock" ]] && cleanup_stale_lock_if_safe "$tmp_err"
    backoff_seconds=0
    if [[ "$attempt" -lt "$OPENCLAW_MAX_RETRIES" ]]; then
      backoff_seconds="$(compute_backoff_seconds "$attempt" "$reason")"
    fi
    record_attempt_result "$attempt" "$agent_id" "$session_id" "$reason" "$rc" "$elapsed_ms" "$lines" "$payload_status" "$backoff_seconds"
    LAST_REASON="$reason"
    LAST_BACKOFF_SECONDS="$backoff_seconds"
    return 1
  fi

  payload_text="$(jq -r '.payloads[0].text // empty' "$tmp_json" 2>/dev/null || true)"
  if [[ -z "$payload_text" ]]; then
    reason="empty_payload"
    backoff_seconds=0
    if [[ "$attempt" -lt "$OPENCLAW_MAX_RETRIES" ]]; then
      backoff_seconds="$(compute_backoff_seconds "$attempt" "$reason")"
    fi
    record_attempt_result "$attempt" "$agent_id" "$session_id" "$reason" 0 "$elapsed_ms" "$lines" "$payload_status" "$backoff_seconds"
    LAST_REASON="$reason"
    LAST_BACKOFF_SECONDS="$backoff_seconds"
    return 1
  fi
  payload_status="text"

  if ! extract_jsonl "$payload_text" "$OUTPUT_FILE"; then
    reason="jsonl_extraction_failed"
    backoff_seconds=0
    if [[ "$attempt" -lt "$OPENCLAW_MAX_RETRIES" ]]; then
      backoff_seconds="$(compute_backoff_seconds "$attempt" "$reason")"
    fi
    record_attempt_result "$attempt" "$agent_id" "$session_id" "$reason" 0 "$elapsed_ms" "$lines" "$payload_status" "$backoff_seconds"
    LAST_REASON="$reason"
    LAST_BACKOFF_SECONDS="$backoff_seconds"
    return 1
  fi

  lines=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
  if validate_quality "$OUTPUT_FILE"; then
    reason="success"
    record_attempt_result "$attempt" "$agent_id" "$session_id" "$reason" 0 "$elapsed_ms" "$lines" "$payload_status" 0
    LAST_REASON="$reason"
    LAST_BACKOFF_SECONDS=0
    return 0
  fi

  reason="quality_fail"
  backoff_seconds=0
  if [[ "$attempt" -lt "$OPENCLAW_MAX_RETRIES" ]]; then
    backoff_seconds="$(compute_backoff_seconds "$attempt" "$reason")"
  fi
  record_attempt_result "$attempt" "$agent_id" "$session_id" "$reason" 0 "$elapsed_ms" "$lines" "$payload_status" "$backoff_seconds"
  LAST_REASON="$reason"
  LAST_BACKOFF_SECONDS="$backoff_seconds"
  return 1
}

summarize_reasons() {
  if [[ ! -s "$REASONS_FILE" ]]; then
    printf '%s' "none"
    return
  fi
  sort "$REASONS_FILE" | uniq -c | sort -rn | head -3 | awk '{printf "%s%s:%s", (NR==1?"":", "), $2, $1}'
}

build_agent_pool

run_start_ms="$(now_ms)"
attempt=1
while [[ "$attempt" -le "$OPENCLAW_MAX_RETRIES" ]]; do
  if run_collection "$attempt"; then
    total_ms=$(( $(now_ms) - run_start_ms ))
    top_reasons="$(summarize_reasons)"
    echo "[openclaw-cli] summary status=success attempts=$attempt total_ms=$total_ms top_reasons=$top_reasons" >> "$META_FILE"
    log_diag_event "run_summary" "\"status\":\"success\",\"attempts\":$attempt,\"total_elapsed_ms\":$total_ms,\"top_reasons\":$(json_escape_string "$top_reasons")"
    exit 0
  fi

  if [[ "$attempt" -lt "$OPENCLAW_MAX_RETRIES" ]]; then
    sleep_seconds="$LAST_BACKOFF_SECONDS"
    if [[ -z "$sleep_seconds" ]] || [[ "$sleep_seconds" -lt 0 ]]; then
      sleep_seconds=0
    fi
    echo "[openclaw-cli] retrying in ${sleep_seconds}s (reason=$LAST_REASON)" >> "$META_FILE"
    sleep "$sleep_seconds"
  fi
  attempt=$((attempt + 1))
done

if [[ -f "$OUTPUT_FILE" ]] && [[ -s "$OUTPUT_FILE" ]]; then
  lines=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
  if [[ "$lines" -gt 1 ]]; then
    total_ms=$(( $(now_ms) - run_start_ms ))
    top_reasons="$(summarize_reasons)"
    echo "[openclaw-cli] summary status=partial attempts=$OPENCLAW_MAX_RETRIES total_ms=$total_ms top_reasons=$top_reasons records=$lines" >> "$META_FILE"
    log_diag_event "run_summary" "\"status\":\"partial\",\"attempts\":$OPENCLAW_MAX_RETRIES,\"total_elapsed_ms\":$total_ms,\"top_reasons\":$(json_escape_string "$top_reasons"),\"records\":$lines"
    exit 0
  fi
fi

echo "[openclaw-cli] all retries exhausted; writing fallback" >> "$META_FILE"
jq -nc --arg ts "$(TZ=Asia/Seoul date +%FT%T%z)" \
  '{country:"GLOBAL",product:"UNKNOWN",pillar:"Collection",brand:"UNKNOWN",signal_type:"collection_failed",value:"All collection attempts failed",currency:"",quote_original:"",source_url:"",collected_at:$ts,confidence:0.1}' \
  > "$OUTPUT_FILE"

total_ms=$(( $(now_ms) - run_start_ms ))
top_reasons="$(summarize_reasons)"
log_diag_event "run_summary" "\"status\":\"failed\",\"attempts\":$OPENCLAW_MAX_RETRIES,\"total_elapsed_ms\":$total_ms,\"top_reasons\":$(json_escape_string "$top_reasons")"
exit 1
