#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATE_KEY="${1:-$(TZ=Asia/Seoul date +%F)}"
START_DATE="${2:-$(TZ=Asia/Seoul date -v-7d +%F)}"
END_DATE="${3:-$(TZ=Asia/Seoul date -v-1d +%F)}"

RAW_FILE="$ROOT_DIR/data/raw/openclaw_${DATE_KEY}.jsonl"
REPORT_FILE="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}.md"
TEMPLATE_FILE="$ROOT_DIR/templates/report_template.md"

mkdir -p "$ROOT_DIR/reports/md" "$ROOT_DIR/qa"

if [[ ! -f "$RAW_FILE" ]]; then
  echo "raw data not found: $RAW_FILE" >&2
  exit 1
fi

PREPARED_BY="${REPORT_PREPARED_BY:-D2C Global Intelligence (OpenClaw Automated)}"
DISTRIBUTION="${REPORT_DISTRIBUTION:-D2C Leadership / Confidential}"
VERSION="${REPORT_VERSION_PREFIX:-Weekly Vol.}${DATE_KEY}-R2"

# 기본 카운트(placeholder): raw line 수를 simple metric으로 사용
TOTAL_SIGNALS="$(wc -l < "$RAW_FILE" | tr -d ' ')"

sed \
  -e "s/{{REPORT_START}}/${START_DATE}/g" \
  -e "s/{{REPORT_END}}/${END_DATE}/g" \
  -e "s/{{PREPARED_BY}}/${PREPARED_BY//\//\\/}/g" \
  -e "s/{{DISTRIBUTION}}/${DISTRIBUTION//\//\\/}/g" \
  -e "s/{{GENERATED_DATE}}/${DATE_KEY}/g" \
  -e "s/{{VERSION}}/${VERSION//\//\\/}/g" \
  "$TEMPLATE_FILE" > "$REPORT_FILE"

{
  echo
  echo "---"
  echo "### Auto-generated Snapshot"
  echo "- 수집 신호 건수(원천 라인 수): ${TOTAL_SIGNALS}"
  echo "- 원천 데이터 파일: \`$RAW_FILE\`"
  echo "- 참고: 본 보고서는 bootstrap 템플릿이며, 실제 운영 시 OpenClaw/Codex 단계에서 상세 수치와 표가 채워집니다."
} >> "$REPORT_FILE"

echo "report generated: $REPORT_FILE"
