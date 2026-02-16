#!/usr/bin/env bash
set -euo pipefail

# Args:
# 1) prompt file
# 2) output file
# 3) metadata log file
PROMPT_FILE="$1"
OUTPUT_FILE="$2"
META_FILE="$3"

# TODO: 실제 OpenClaw 실행 커맨드로 교체
# 예시 형태:
# openclaw run --prompt-file "$PROMPT_FILE" --output "$OUTPUT_FILE"

{
  echo "[example-openclaw-runner] using prompt: $PROMPT_FILE"
  echo "[example-openclaw-runner] writing mock output"
} >> "$META_FILE"

cat > "$OUTPUT_FILE" <<JSONL
{"country":"US","product":"Monitor","pillar":"Competitive Price & Positioning","brand":"LG","signal_type":"price","value":"699","currency":"USD","quote_original":"","source_url":"https://www.google.com/search?q=LG+UltraGear+price+US+this+week","collected_at":"$(TZ=Asia/Seoul date +%FT%T%z)","confidence":0.4}
JSONL
