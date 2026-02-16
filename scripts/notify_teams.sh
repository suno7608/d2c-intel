#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/config/pipeline.env"
PRESET_TEAMS_WEBHOOK_URL="${TEAMS_WEBHOOK_URL:-}"
PRESET_TEAMS_DRY_RUN="${TEAMS_DRY_RUN:-}"
PRESET_SHARED_BASE_URL="${SHARED_BASE_URL:-}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -n "$PRESET_TEAMS_WEBHOOK_URL" ]]; then
  export TEAMS_WEBHOOK_URL="$PRESET_TEAMS_WEBHOOK_URL"
fi
if [[ -n "$PRESET_TEAMS_DRY_RUN" ]]; then
  export TEAMS_DRY_RUN="$PRESET_TEAMS_DRY_RUN"
fi
if [[ -n "$PRESET_SHARED_BASE_URL" ]]; then
  export SHARED_BASE_URL="$PRESET_SHARED_BASE_URL"
fi

DATE_KEY="${1:-$(TZ=Asia/Seoul date +%F)}"
FINAL_MD_INPUT="${2:-}"
TEAMS_DRY_RUN="${TEAMS_DRY_RUN:-0}"

if [[ -n "$FINAL_MD_INPUT" && -f "$FINAL_MD_INPUT" ]]; then
  FINAL_MD="$FINAL_MD_INPUT"
else
  FINAL_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_R2_16country.md"
  [[ -f "$FINAL_MD" ]] || FINAL_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_claude.md"
  [[ -f "$FINAL_MD" ]] || FINAL_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}.md"
fi

if [[ ! -f "$FINAL_MD" ]]; then
  echo "Final markdown not found for teams notification: $DATE_KEY" >&2
  exit 1
fi

if [[ -z "${TEAMS_WEBHOOK_URL:-}" && "$TEAMS_DRY_RUN" != "1" ]]; then
  echo "TEAMS_WEBHOOK_URL is not set. teams notify skipped." >&2
  exit 0
fi

HUB_LINK="$ROOT_DIR/reports/html/latest/hub.html"
WEEK_HTML_LINK="$ROOT_DIR/reports/html/$DATE_KEY/index.html"
WEEK_PDF_LINK="$ROOT_DIR/reports/pdf/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_R2_16country.pdf"

if [[ -n "${SHARED_BASE_URL:-}" ]]; then
  BASE="${SHARED_BASE_URL%/}"
  HUB_LINK="$BASE/latest/html/hub.html"
  WEEK_HTML_LINK="$BASE/weekly/$DATE_KEY/html/index.html"
  WEEK_PDF_LINK="$BASE/weekly/$DATE_KEY/pdf/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_R2_16country.pdf"
fi

TITLE="LG Global D2C Weekly Intelligence - ${DATE_KEY} 발행 완료"
TEXT="주간 보고서가 발행되었습니다.<br/><br/>"
TEXT+="- Hub: <a href='${HUB_LINK}'>Open Hub</a><br/>"
TEXT+="- Week HTML: <a href='${WEEK_HTML_LINK}'>Open HTML</a><br/>"
TEXT+="- Week PDF: <a href='${WEEK_PDF_LINK}'>Download PDF</a><br/>"
TEXT+="- Source MD: ${FINAL_MD}<br/>"
TEXT+="- Generated at: $(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M:%S KST')"

PAYLOAD_FILE="$(mktemp)"
cat > "$PAYLOAD_FILE" <<JSON
{
  "@type": "MessageCard",
  "@context": "http://schema.org/extensions",
  "summary": "LG D2C Weekly Report ${DATE_KEY}",
  "themeColor": "005A9C",
  "title": "${TITLE}",
  "text": "${TEXT}"
}
JSON

if [[ "$TEAMS_DRY_RUN" == "1" ]]; then
  echo "TEAMS_DRY_RUN=1"
  cat "$PAYLOAD_FILE"
  rm -f "$PAYLOAD_FILE"
  exit 0
fi

curl -fsS -X POST -H "Content-Type: application/json" --data-binary "@$PAYLOAD_FILE" "$TEAMS_WEBHOOK_URL"
rm -f "$PAYLOAD_FILE"

echo "Teams notification sent: $DATE_KEY"
