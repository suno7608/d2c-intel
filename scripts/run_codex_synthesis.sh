#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATE_KEY="${1:-$(TZ=Asia/Seoul date +%F)}"
START_DATE="${2:-$(TZ=Asia/Seoul date -v-7d +%F)}"
END_DATE="${3:-$(TZ=Asia/Seoul date -v-1d +%F)}"

RAW_FILE="$ROOT_DIR/data/raw/openclaw_${DATE_KEY}.jsonl"
REPORT_FILE="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}.md"

# ⚠️ 기존 리포트 보호 — Claude 생성본이 이미 있으면 덮어쓰지 않는다
CLAUDE_FILE="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_claude.md"
if [[ -f "$CLAUDE_FILE" ]] && [[ $(wc -c < "$CLAUDE_FILE") -gt 40000 ]]; then
  echo "WARNING: Claude report already exists ($(wc -c < "$CLAUDE_FILE") bytes). Skipping synthesis to prevent overwrite."
  echo "To force, delete $CLAUDE_FILE first."
  exit 0
fi
REPORT_FILE_R2="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_R2_16country.md"
GENERATOR="$ROOT_DIR/scripts/generate_weekly_markdown.py"

mkdir -p "$ROOT_DIR/reports/md" "$ROOT_DIR/qa"

if [[ ! -f "$RAW_FILE" ]]; then
  echo "raw data not found: $RAW_FILE" >&2
  exit 1
fi

PREPARED_BY="${REPORT_PREPARED_BY:-D2C Global Intelligence (OpenClaw Automated)}"
DISTRIBUTION="${REPORT_DISTRIBUTION:-D2C Leadership / Confidential}"
VERSION="${REPORT_VERSION_PREFIX:-Weekly Vol.}${DATE_KEY}-R2"

if [[ ! -f "$GENERATOR" ]]; then
  echo "generator not found: $GENERATOR" >&2
  exit 1
fi

python3 "$GENERATOR" \
  "$ROOT_DIR" \
  "$DATE_KEY" \
  "$START_DATE" \
  "$END_DATE" \
  "$REPORT_FILE" \
  "$PREPARED_BY" \
  "$DISTRIBUTION" \
  "$VERSION"

cp "$REPORT_FILE" "$REPORT_FILE_R2"

echo "report generated: $REPORT_FILE"
