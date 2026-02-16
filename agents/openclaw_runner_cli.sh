#!/usr/bin/env bash
set -euo pipefail

PROMPT_FILE="$1"
OUTPUT_FILE="$2"
META_FILE="$3"

OPENCLAW_AGENT_ID="${OPENCLAW_AGENT_ID:-main}"
OPENCLAW_TIMEOUT_SECONDS="${OPENCLAW_TIMEOUT_SECONDS:-600}"

TMP_JSON="$(mktemp)"
trap 'rm -f "$TMP_JSON"' EXIT

PROMPT_TEXT="$(cat "$PROMPT_FILE")"

MIN_RECORDS="${MIN_RECORDS:-50}"
MIN_COUNTRIES="${MIN_COUNTRIES:-10}"
MAX_RETRIES="${MAX_RETRIES:-2}"

extract_jsonl() {
  local source="$1"
  local dest="$2"
  
  # 1) 전체가 valid JSON array인지
  if echo "$source" | jq -e 'type == "array"' >/dev/null 2>&1; then
    echo "$source" | jq -c '.[]' > "$dest"
    return 0
  fi
  
  # 2) 전체가 valid JSON object인지
  if echo "$source" | jq -e 'type == "object"' >/dev/null 2>&1; then
    echo "$source" | jq -c '.' > "$dest"
    return 0
  fi
  
  # 3) 텍스트에서 JSON 라인 추출
  local extracted
  extracted=$(echo "$source" | grep -E '^\s*\{' | while IFS= read -r line; do
    echo "$line" | jq -c '.' 2>/dev/null
  done)
  
  if [[ -n "$extracted" ]]; then
    echo "$extracted" > "$dest"
    return 0
  fi
  
  return 1
}

validate_quality() {
  local file="$1"
  local record_count country_count product_counts
  
  record_count=$(wc -l < "$file" | tr -d ' ')
  country_count=$(jq -r '.country' "$file" 2>/dev/null | sort -u | wc -l | tr -d ' ')
  
  # 제품별 건수 체크
  product_counts=$(jq -r '.product' "$file" 2>/dev/null | sort | uniq -c | sort -rn)
  local tv_count fridge_count washer_count monitor_count gram_count
  tv_count=$(echo "$product_counts" | grep -i "TV" | awk '{print $1}' || echo 0)
  fridge_count=$(echo "$product_counts" | grep -i "Refrigerator" | awk '{print $1}' || echo 0)
  washer_count=$(echo "$product_counts" | grep -i "Washing" | awk '{print $1}' || echo 0)
  monitor_count=$(echo "$product_counts" | grep -i "Monitor" | awk '{print $1}' || echo 0)
  gram_count=$(echo "$product_counts" | grep -i "gram" | awk '{print $1}' || echo 0)
  
  # Confidence 비율 체크
  local low_conf_count low_conf_pct
  low_conf_count=$(jq -r '.confidence' "$file" 2>/dev/null | grep -ci "low" || echo 0)
  low_conf_pct=$((low_conf_count * 100 / (record_count > 0 ? record_count : 1)))
  
  {
    echo "[quality] records=$record_count countries=$country_count (min: records=$MIN_RECORDS countries=$MIN_COUNTRIES)"
    echo "[quality] products: TV=$tv_count Fridge=$fridge_count Washer=$washer_count Monitor=$monitor_count gram=$gram_count"
    echo "[quality] confidence: low=$low_conf_count (${low_conf_pct}%) — warning threshold: 20%"
    if [[ "$low_conf_pct" -gt 20 ]]; then
      echo "[quality] ⚠️ WARNING: low confidence ratio exceeds 20% — data quality risk"
    fi
  } >> "$META_FILE"
  
  if [[ "$record_count" -ge "$MIN_RECORDS" ]] && [[ "$country_count" -ge "$MIN_COUNTRIES" ]]; then
    return 0
  fi
  return 1
}

run_collection() {
  local attempt="$1"
  local session_id
  session_id="$(uuidgen | tr 'A-Z' 'a-z')"
  
  {
    echo "[openclaw-cli] attempt=$attempt agent=$OPENCLAW_AGENT_ID"
    echo "[openclaw-cli] timeout=${OPENCLAW_TIMEOUT_SECONDS}s session_id=$session_id"
  } >> "$META_FILE"
  
  if ! perl -e 'my $t=shift @ARGV; local $SIG{ALRM}=sub{exit 124}; alarm $t; my $rc=system @ARGV; alarm 0; exit($rc == -1 ? 125 : ($rc >> 8));' "$OPENCLAW_TIMEOUT_SECONDS" \
    openclaw agent --agent "$OPENCLAW_AGENT_ID" --session-id "$session_id" --local --json --timeout "$OPENCLAW_TIMEOUT_SECONDS" --message "$PROMPT_TEXT" \
    > "$TMP_JSON" 2>> "$META_FILE"; then
    echo "[openclaw-cli] attempt $attempt: command failed or timed out" >> "$META_FILE"
    return 1
  fi
  
  local payload_text
  payload_text="$(jq -r '.payloads[0].text // empty' "$TMP_JSON")"
  
  if [[ -z "$payload_text" ]]; then
    echo "[openclaw-cli] attempt $attempt: empty payload" >> "$META_FILE"
    return 1
  fi
  
  if ! extract_jsonl "$payload_text" "$OUTPUT_FILE"; then
    echo "[openclaw-cli] attempt $attempt: JSONL extraction failed" >> "$META_FILE"
    return 1
  fi
  
  local lines
  lines=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
  echo "[openclaw-cli] attempt $attempt: extracted $lines records" >> "$META_FILE"
  
  if validate_quality "$OUTPUT_FILE"; then
    echo "[openclaw-cli] attempt $attempt: QUALITY PASS ✅" >> "$META_FILE"
    return 0
  else
    echo "[openclaw-cli] attempt $attempt: QUALITY FAIL ❌ (below minimum threshold)" >> "$META_FILE"
    return 1
  fi
}

# Main: 최대 MAX_RETRIES 번 시도
for attempt in $(seq 1 "$MAX_RETRIES"); do
  if run_collection "$attempt"; then
    exit 0
  fi
  if [[ "$attempt" -lt "$MAX_RETRIES" ]]; then
    echo "[openclaw-cli] retrying in 10s..." >> "$META_FILE"
    sleep 10
  fi
done

# 모든 시도 실패 시: 부분 데이터라도 있으면 사용, 없으면 fallback
if [[ -f "$OUTPUT_FILE" ]] && [[ -s "$OUTPUT_FILE" ]]; then
  lines=$(wc -l < "$OUTPUT_FILE" | tr -d ' ')
  if [[ "$lines" -gt 1 ]]; then
    echo "[openclaw-cli] all retries exhausted but using partial data ($lines records)" >> "$META_FILE"
    exit 0
  fi
fi

echo "[openclaw-cli] all retries exhausted; writing fallback" >> "$META_FILE"
jq -nc --arg ts "$(TZ=Asia/Seoul date +%FT%T%z)" \
  '{country:"GLOBAL",product:"UNKNOWN",pillar:"Collection",brand:"UNKNOWN",signal_type:"collection_failed",value:"All collection attempts failed",currency:"",quote_original:"",source_url:"",collected_at:$ts,confidence:0.1}' \
  > "$OUTPUT_FILE"
exit 1
