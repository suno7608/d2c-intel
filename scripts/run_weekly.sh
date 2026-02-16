#!/usr/bin/env bash
set -euo pipefail

# 절전 방지 — 파이프라인 완료까지 Mac을 깨운 상태 유지
if [[ -z "${CAFFEINATED:-}" ]]; then
  export CAFFEINATED=1
  exec caffeinate -i -s bash "$0" "$@"
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/config/pipeline.env"
PRESET_OPENCLAW_RUNNER="${OPENCLAW_RUNNER:-}"
PRESET_CLAUDE_RUNNER="${CLAUDE_RUNNER:-}"
PRESET_CLAUDE_TIMEOUT_SECONDS="${CLAUDE_TIMEOUT_SECONDS:-}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ -n "$PRESET_OPENCLAW_RUNNER" ]]; then
  export OPENCLAW_RUNNER="$PRESET_OPENCLAW_RUNNER"
fi
if [[ -n "$PRESET_CLAUDE_RUNNER" ]]; then
  export CLAUDE_RUNNER="$PRESET_CLAUDE_RUNNER"
fi
if [[ -n "$PRESET_CLAUDE_TIMEOUT_SECONDS" ]]; then
  export CLAUDE_TIMEOUT_SECONDS="$PRESET_CLAUDE_TIMEOUT_SECONDS"
fi

export TZ="${TZ:-Asia/Seoul}"

DATE_KEY="${1:-$(date +%F)}"
# Sunday 04:00 KST 실행: 보고구간은 전주 일요일~토요일
# 실행일이 일요일이면: START = 7일 전(전주 일요일), END = 1일 전(토요일)
START_DATE="${2:-$(date -v-7d +%F)}"
END_DATE="${3:-$(date -v-1d +%F)}"

LOG_FILE="$ROOT_DIR/logs/pipeline_${DATE_KEY}.log"

{
  echo "[pipeline] start date_key=$DATE_KEY"
  echo "[pipeline] period=$START_DATE to $END_DATE"

  # Gmail 토큰 사전 검증
  python3 "$ROOT_DIR/scripts/check_gmail_token.py" || echo "[pipeline] ⚠️ Gmail token check failed — email delivery may fail"

  bash "$ROOT_DIR/scripts/run_openclaw_collection.sh" "$DATE_KEY"

  # W-o-W 통계 자동 저장
  bash "$ROOT_DIR/scripts/save_weekly_stats.sh" "$DATE_KEY" || echo "[pipeline] stats save failed (non-fatal)"

  bash "$ROOT_DIR/scripts/run_codex_synthesis.sh" "$DATE_KEY" "$START_DATE" "$END_DATE"
  bash "$ROOT_DIR/scripts/run_claude_cowork.sh" "$DATE_KEY"
  bash "$ROOT_DIR/scripts/render_html.sh" "$DATE_KEY"

  echo "[pipeline] done"
} | tee "$LOG_FILE"

FINAL_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_claude.md"
[[ -f "$FINAL_MD" ]] || FINAL_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}.md"
if [[ ! -f "$FINAL_MD" ]]; then
  echo "Final markdown not found: $FINAL_MD" >&2
  exit 1
fi

if [[ "${ENABLE_PUBLISHABLE_BUILD:-1}" == "1" ]]; then
  bash "$ROOT_DIR/scripts/build_publishable_report.sh" "$DATE_KEY" "$FINAL_MD"
fi

if [[ "${ENABLE_OBSIDIAN_EXPORT:-0}" == "1" ]]; then
  bash "$ROOT_DIR/scripts/export_obsidian_weekly.sh" "$DATE_KEY" "$FINAL_MD"
fi

if [[ "${ENABLE_SHARED_PUBLISH:-0}" == "1" ]]; then
  bash "$ROOT_DIR/scripts/publish_to_shared.sh" "$DATE_KEY" "$FINAL_MD"
fi

if [[ "${ENABLE_TEAMS_NOTIFY:-0}" == "1" ]]; then
  bash "$ROOT_DIR/scripts/notify_teams.sh" "$DATE_KEY" "$FINAL_MD"
fi

echo "Final Markdown: $FINAL_MD"
echo "Final HTML: $ROOT_DIR/reports/html/${DATE_KEY}/index.html"
echo "Final PDF: $ROOT_DIR/reports/pdf/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_R2_16country.pdf"
echo "Latest Hub: $ROOT_DIR/reports/html/latest/hub.html"
echo "Shared Root: ${SHARED_PUBLISH_ROOT:-disabled}"
echo "Teams Notify: ${ENABLE_TEAMS_NOTIFY:-0}"
echo "Log: $LOG_FILE"
