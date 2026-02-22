#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATE_KEY="${1:-$(TZ=Asia/Seoul date +%F)}"

RAW_FILE="$ROOT_DIR/data/raw/openclaw_${DATE_KEY}.jsonl"
FALLBACK_MARKER="$ROOT_DIR/data/raw/openclaw_${DATE_KEY}.fallback_from"
KO_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_claude.md"
[[ -f "$KO_MD" ]] || KO_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}.md"
EN_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_en.md"
KO_HTML="$ROOT_DIR/reports/html/${DATE_KEY}/index.html"
EN_HTML="$ROOT_DIR/reports/html/${DATE_KEY}/index_en.html"
HUB_HTML="$ROOT_DIR/reports/html/latest/hub.html"
HUB_EN_HTML="$ROOT_DIR/reports/html/latest/hub_en.html"
META_FILE="$ROOT_DIR/reports/html/${DATE_KEY}/metadata.json"

MIN_RECORDS="${MIN_RECORDS:-200}"
MIN_COUNTRIES="${MIN_COUNTRIES:-13}"
MIN_FRIDGE="${MIN_FRIDGE:-40}"
MIN_WASHER="${MIN_WASHER:-35}"
MIN_MONITOR="${MIN_MONITOR:-15}"
MIN_GRAM="${MIN_GRAM:-10}"
MAX_TV_RATIO="${MAX_TV_RATIO:-45}"
FAIL_ON_STALE_COLLECTION="${FAIL_ON_STALE_COLLECTION:-0}"

fail_count=0

pass() {
  echo "[quality] ✅ $1"
}

fail() {
  echo "[quality] ❌ $1" >&2
  fail_count=$((fail_count + 1))
}

require_file() {
  local f="$1"
  if [[ -f "$f" ]]; then
    pass "exists: $f"
  else
    fail "missing file: $f"
  fi
}

echo "[quality] start date=$DATE_KEY"

for cmd in jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[quality] missing required command: $cmd" >&2
    exit 1
  fi
done

require_file "$RAW_FILE"
require_file "$KO_MD"
require_file "$KO_HTML"
require_file "$EN_HTML"
require_file "$HUB_HTML"
require_file "$HUB_EN_HTML"
require_file "$META_FILE"

if [[ ! -f "$RAW_FILE" ]]; then
  echo "[quality] aborted (raw data missing)" >&2
  exit 1
fi

if [[ -f "$FALLBACK_MARKER" ]]; then
  fallback_date="$(cat "$FALLBACK_MARKER" 2>/dev/null | tr -d '[:space:]')"
  if [[ "$fallback_date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    fallback_age="$(python3 - <<PY
import datetime
today=datetime.date.fromisoformat("${DATE_KEY}")
fallback=datetime.date.fromisoformat("${fallback_date}")
print((today-fallback).days)
PY
)"
    msg="stale collection fallback detected: ${fallback_date} (${fallback_age}d old)"
    if [[ "$FAIL_ON_STALE_COLLECTION" == "1" ]]; then
      fail "$msg"
    else
      echo "[quality] ⚠️ $msg"
    fi
  else
    msg="stale collection fallback marker found but malformed: $FALLBACK_MARKER"
    if [[ "$FAIL_ON_STALE_COLLECTION" == "1" ]]; then
      fail "$msg"
    else
      echo "[quality] ⚠️ $msg"
    fi
  fi
fi

records="$(wc -l < "$RAW_FILE" | tr -d ' ')"
countries="$(jq -r '.country // empty' "$RAW_FILE" 2>/dev/null | sort -u | wc -l | tr -d ' ')"
tv_count="$(jq -r '.product // empty' "$RAW_FILE" | awk 'BEGIN{n=0} tolower($0)=="tv"{n++} END{print n+0}')"
fridge_count="$(jq -r '.product // empty' "$RAW_FILE" | awk 'BEGIN{n=0} tolower($0)=="refrigerator"{n++} END{print n+0}')"
washer_count="$(jq -r '.product // empty' "$RAW_FILE" | awk 'BEGIN{n=0} tolower($0)=="washing machine"{n++} END{print n+0}')"
monitor_count="$(jq -r '.product // empty' "$RAW_FILE" | awk 'BEGIN{n=0} tolower($0)=="monitor"{n++} END{print n+0}')"
gram_count="$(jq -r '.product // empty' "$RAW_FILE" | awk 'BEGIN{n=0} tolower($0)=="lg gram"{n++} END{print n+0}')"
tv_ratio="$(awk -v tv="$tv_count" -v total="$records" 'BEGIN{if(total==0){print 0}else{printf "%.1f", (tv*100)/total}}')"

[[ "$records" -ge "$MIN_RECORDS" ]] && pass "record count ${records} >= ${MIN_RECORDS}" || fail "record count ${records} < ${MIN_RECORDS}"
[[ "$countries" -ge "$MIN_COUNTRIES" ]] && pass "country count ${countries} >= ${MIN_COUNTRIES}" || fail "country count ${countries} < ${MIN_COUNTRIES}"
[[ "$fridge_count" -ge "$MIN_FRIDGE" ]] && pass "refrigerator count ${fridge_count} >= ${MIN_FRIDGE}" || fail "refrigerator count ${fridge_count} < ${MIN_FRIDGE}"
[[ "$washer_count" -ge "$MIN_WASHER" ]] && pass "washing machine count ${washer_count} >= ${MIN_WASHER}" || fail "washing machine count ${washer_count} < ${MIN_WASHER}"
[[ "$monitor_count" -ge "$MIN_MONITOR" ]] && pass "monitor count ${monitor_count} >= ${MIN_MONITOR}" || fail "monitor count ${monitor_count} < ${MIN_MONITOR}"
[[ "$gram_count" -ge "$MIN_GRAM" ]] && pass "gram count ${gram_count} >= ${MIN_GRAM}" || fail "gram count ${gram_count} < ${MIN_GRAM}"
awk -v r="$tv_ratio" -v max="$MAX_TV_RATIO" 'BEGIN{exit !(r<=max)}' && pass "tv ratio ${tv_ratio}% <= ${MAX_TV_RATIO}%" || fail "tv ratio ${tv_ratio}% > ${MAX_TV_RATIO}%"

if grep -q "placeholder" "$RAW_FILE"; then
  fail "placeholder data detected in raw collection file"
else
  pass "no placeholder records in raw collection file"
fi

if grep -qE "\(작성\)|TODO|TBD" "$KO_MD"; then
  fail "template placeholders found in Korean markdown"
else
  pass "no template placeholders in Korean markdown"
fi

if [[ -f "$EN_MD" ]]; then
  pass "exists: $EN_MD"
  if grep -qP "[가-힣]" "$EN_MD"; then
    echo "[quality] ⚠️ Hangul detected in English markdown (legacy file or pre-migration output)"
  else
    pass "no Hangul in English markdown"
  fi
  if grep -qw "translated" "$EN_MD"; then
    echo "[quality] ⚠️ literal token 'translated' detected in English markdown (legacy file or pre-migration output)"
  else
    pass "no literal token 'translated' in English markdown"
  fi
else
  echo "[quality] ⚠️ English markdown missing: $EN_MD (skipped)"
fi

if grep -qP "[가-힣]" "$EN_HTML"; then
  fail "Hangul detected in English HTML"
else
  pass "no Hangul in English HTML"
fi

if grep -qw "translated" "$EN_HTML"; then
  fail "literal token 'translated' detected in English HTML"
else
  pass "no literal token 'translated' in English HTML"
fi

if grep -q 'href="file://' "$HUB_HTML" "$HUB_EN_HTML"; then
  fail "file:// href detected in hub links"
else
  pass "no file:// href in hub links"
fi

null_metrics="$(jq -r '.metrics | to_entries[] | select(.value == null) | .key' "$META_FILE" | wc -l | tr -d ' ')"
if [[ "$null_metrics" -gt 0 ]]; then
  fail "metadata contains null metric values"
else
  pass "metadata metric values are non-null"
fi

if jq -e '.critical_countries[]? | test("^[0-9]")' "$META_FILE" >/dev/null 2>&1; then
  fail "metadata critical_countries contains malformed numeric text entries"
else
  pass "metadata critical_countries format looks valid"
fi

if [[ "$fail_count" -gt 0 ]]; then
  echo "[quality] failed with ${fail_count} issue(s)" >&2
  exit 1
fi

echo "[quality] all checks passed"
