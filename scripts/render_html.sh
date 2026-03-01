#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATE_KEY="${1:-$(TZ=Asia/Seoul date +%F)}"
SOURCE_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_claude.md"
TARGET_DIR="$ROOT_DIR/reports/html/${DATE_KEY}"
TARGET_HTML="$TARGET_DIR/index.html"

mkdir -p "$TARGET_DIR"

if [[ ! -f "$SOURCE_MD" ]]; then
  SOURCE_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}.md"
fi

if [[ ! -f "$SOURCE_MD" ]]; then
  echo "source markdown not found" >&2
  exit 1
fi

# Use professional renderer (marked library)
if [[ -f "$ROOT_DIR/scripts/render_professional_report.mjs" ]]; then
  node "$ROOT_DIR/scripts/render_professional_report.mjs" "$SOURCE_MD" "$TARGET_HTML" "ko"
elif command -v pandoc >/dev/null 2>&1; then
  pandoc "$SOURCE_MD" -o "$TARGET_HTML" --standalone --metadata title="LG Global D2C Weekly Intelligence"
else
  echo "WARNING: No renderer available (no render_professional_report.mjs, no pandoc)" >&2
  echo "Generating basic HTML fallback" >&2
  {
    echo "<!doctype html>"
    echo "<html lang=\"ko\"><head><meta charset=\"utf-8\">"
    echo "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
    echo "<title>LG Global D2C Weekly Intelligence</title>"
    echo "<style>body{font-family:Arial,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;line-height:1.6}pre{white-space:pre-wrap}</style>"
    echo "</head><body><h1>LG Global D2C Weekly Intelligence</h1><pre>"
    sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g' "$SOURCE_MD"
    echo "</pre></body></html>"
  } > "$TARGET_HTML"
fi

echo "html generated: $TARGET_HTML"
