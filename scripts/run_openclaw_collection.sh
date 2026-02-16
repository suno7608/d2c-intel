#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATE_KEY="${1:-$(TZ=Asia/Seoul date +%F)}"
PROMPT_FILE="$ROOT_DIR/prompts/openclaw_collection_brief.md"
OUTPUT_FILE="$ROOT_DIR/data/raw/openclaw_${DATE_KEY}.jsonl"
META_FILE="$ROOT_DIR/logs/openclaw_${DATE_KEY}.log"

mkdir -p "$ROOT_DIR/data/raw" "$ROOT_DIR/logs"

echo "[openclaw] date=$DATE_KEY" | tee "$META_FILE"
echo "[openclaw] prompt=$PROMPT_FILE" | tee -a "$META_FILE"

if [[ -n "${OPENCLAW_RUNNER:-}" ]]; then
  echo "[openclaw] running external runner" | tee -a "$META_FILE"
  "$OPENCLAW_RUNNER" "$PROMPT_FILE" "$OUTPUT_FILE" "$META_FILE"
else
  echo "[openclaw] OPENCLAW_RUNNER not set. writing bootstrap placeholder data" | tee -a "$META_FILE"
  cat > "$OUTPUT_FILE" <<JSONL
{"country":"US","product":"TV","pillar":"Consumer Sentiment","brand":"LG","signal_type":"quote","value":"placeholder","currency":"USD","quote_original":"placeholder quote","source_url":"https://www.google.com/search?q=LG+OLED+review+past+7+days","collected_at":"${DATE_KEY}T04:00:00+09:00","confidence":0.3}
{"country":"UK","product":"Refrigerator","pillar":"Retail Channel Promotions","brand":"LG","signal_type":"promo","value":"placeholder","currency":"GBP","quote_original":"","source_url":"https://www.google.com/search?q=Currys+LG+fridge+deal+this+week","collected_at":"${DATE_KEY}T04:00:00+09:00","confidence":0.3}
JSONL
fi

echo "[openclaw] output=$OUTPUT_FILE" | tee -a "$META_FILE"
