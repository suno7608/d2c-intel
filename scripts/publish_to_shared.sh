#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/config/pipeline.env"
PRESET_SHARED_PUBLISH_ROOT="${SHARED_PUBLISH_ROOT:-}"
PRESET_SHARED_BASE_URL="${SHARED_BASE_URL:-}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -n "$PRESET_SHARED_PUBLISH_ROOT" ]]; then
  export SHARED_PUBLISH_ROOT="$PRESET_SHARED_PUBLISH_ROOT"
fi
if [[ -n "$PRESET_SHARED_BASE_URL" ]]; then
  export SHARED_BASE_URL="$PRESET_SHARED_BASE_URL"
fi

DATE_KEY="${1:-$(TZ=Asia/Seoul date +%F)}"
FINAL_MD_INPUT="${2:-}"

if [[ -z "${SHARED_PUBLISH_ROOT:-}" ]]; then
  echo "SHARED_PUBLISH_ROOT is not set. shared publish skipped." >&2
  exit 0
fi

if [[ -n "$FINAL_MD_INPUT" && -f "$FINAL_MD_INPUT" ]]; then
  FINAL_MD="$FINAL_MD_INPUT"
else
  FINAL_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_R2_16country.md"
  [[ -f "$FINAL_MD" ]] || FINAL_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_claude.md"
  [[ -f "$FINAL_MD" ]] || FINAL_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}.md"
fi

if [[ ! -f "$FINAL_MD" ]]; then
  echo "Final markdown not found for publish: $DATE_KEY" >&2
  exit 1
fi

WEEK_DIR="$SHARED_PUBLISH_ROOT/weekly/$DATE_KEY"
LATEST_DIR="$SHARED_PUBLISH_ROOT/latest"
mkdir -p "$WEEK_DIR" "$LATEST_DIR"

WEEK_HTML_DIR="$ROOT_DIR/reports/html/$DATE_KEY"
LATEST_HTML_DIR="$ROOT_DIR/reports/html/latest"
PDF_WEEK="$ROOT_DIR/reports/pdf/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_R2_16country.pdf"
PDF_LATEST="$ROOT_DIR/reports/pdf/LG_Global_D2C_Weekly_Intelligence_latest.pdf"

[[ -d "$WEEK_HTML_DIR" ]] || { echo "missing weekly html dir: $WEEK_HTML_DIR" >&2; exit 1; }
[[ -d "$LATEST_HTML_DIR" ]] || { echo "missing latest html dir: $LATEST_HTML_DIR" >&2; exit 1; }

rsync -a --delete "$WEEK_HTML_DIR/" "$WEEK_DIR/html/"
rsync -a --delete "$LATEST_HTML_DIR/" "$LATEST_DIR/html/"

mkdir -p "$WEEK_DIR/pdf" "$LATEST_DIR/pdf" "$WEEK_DIR/md"
if [[ -f "$PDF_WEEK" ]]; then
  cp "$PDF_WEEK" "$WEEK_DIR/pdf/"
fi
if [[ -f "$PDF_LATEST" ]]; then
  cp "$PDF_LATEST" "$LATEST_DIR/pdf/"
fi
cp "$FINAL_MD" "$WEEK_DIR/md/"

MANIFEST_SRC="$ROOT_DIR/reports/html/manifest.json"
if [[ -f "$MANIFEST_SRC" ]]; then
  cp "$MANIFEST_SRC" "$LATEST_DIR/manifest.json"
fi

LINKS_FILE="$WEEK_DIR/share-links.txt"
HUB_PATH="$LATEST_DIR/html/hub.html"
WEEK_HTML_PATH="$WEEK_DIR/html/index.html"
WEEK_PDF_PATH="$WEEK_DIR/pdf/$(basename "$PDF_WEEK")"

{
  echo "# LG Global D2C Weekly Intelligence Share Links"
  echo "date_key=$DATE_KEY"
  echo "local_hub=$HUB_PATH"
  echo "local_week_html=$WEEK_HTML_PATH"
  echo "local_week_pdf=$WEEK_PDF_PATH"
  if [[ -n "${SHARED_BASE_URL:-}" ]]; then
    BASE="${SHARED_BASE_URL%/}"
    echo "hub_url=$BASE/latest/html/hub.html"
    echo "week_html_url=$BASE/weekly/$DATE_KEY/html/index.html"
    echo "week_pdf_url=$BASE/weekly/$DATE_KEY/pdf/$(basename "$PDF_WEEK")"
  fi
} > "$LINKS_FILE"

echo "Shared publish completed"
echo "Weekly dir: $WEEK_DIR"
echo "Latest dir: $LATEST_DIR"
echo "Share links: $LINKS_FILE"
