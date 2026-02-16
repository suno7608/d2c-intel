#!/usr/bin/env bash
set -euo pipefail

# 절전 방지 — 파이프라인 완료까지 Mac을 깨운 상태 유지
if [[ -z "${CAFFEINATED:-}" ]]; then
  export CAFFEINATED=1
  exec caffeinate -i -s bash "$0" "$@"
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/config/pipeline.env"

PRESERVE_ENV_VARS=(
  OPENCLAW_RUNNER
  OPENCLAW_AGENT_ID
  OPENCLAW_TIMEOUT_SECONDS
  OPENCLAW_ALT_AGENT_IDS
  OPENCLAW_MAX_RETRIES
  OPENCLAW_BACKOFF_BASE_SECONDS
  OPENCLAW_BACKOFF_MULTIPLIER
  OPENCLAW_BACKOFF_CAP_SECONDS
  OPENCLAW_JITTER_MAX_SECONDS
  OPENCLAW_RATE_LIMIT_EXTRA_SECONDS
  OPENCLAW_SESSION_LOCK_EXTRA_SECONDS
  OPENCLAW_ENABLE_STALE_LOCK_CLEANUP
  OPENCLAW_ADAPTIVE_POLICY_MAX_LEVEL
  CLAUDE_RUNNER
  CLAUDE_TIMEOUT_SECONDS
  CLAUDE_TRANSLATE_TIMEOUT_SECONDS
  ENABLE_GOOGLE_TRANSLATE_FALLBACK
  ENABLE_OFFLINE_EN_STUB_FALLBACK
  ENABLE_OPENCLAW_LAST_SUCCESS_FALLBACK
  MAX_COLLECTION_STALENESS_DAYS
  ENABLE_PREFLIGHT_CHECK
  PREFLIGHT_FAIL_OPEN
  ENABLE_PREFLIGHT_OPENCLAW_SMOKE
  OPENCLAW_SMOKE_TIMEOUT_SECONDS
  ENABLE_PUBLISHABLE_BUILD
  ENABLE_QUALITY_GATE
  FAIL_ON_STALE_COLLECTION
  ENABLE_OBSIDIAN_EXPORT
  ENABLE_SHARED_PUBLISH
  ENABLE_TEAMS_NOTIFY
)

preserve_env_overrides() {
  local name
  for name in "${PRESERVE_ENV_VARS[@]}"; do
    if [[ "${!name+x}" == "x" ]]; then
      eval "PRESET_${name}=\${$name}"
      eval "PRESET_${name}_SET=1"
    fi
  done
}

restore_env_overrides() {
  local name marker
  for name in "${PRESERVE_ENV_VARS[@]}"; do
    marker="$(eval "printf '%s' \"\${PRESET_${name}_SET:-0}\"")"
    if [[ "$marker" == "1" ]]; then
      eval "export $name=\"\${PRESET_${name}}\""
    fi
  done
}

preserve_env_overrides

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

restore_env_overrides

export TZ="${TZ:-Asia/Seoul}"

DATE_KEY="${1:-$(date +%F)}"
# 보고구간은 전주 일요일~토요일(7일)로 고정
if ! python3 - <<PY >/dev/null 2>&1
import datetime
datetime.date.fromisoformat("${DATE_KEY}")
PY
then
  echo "invalid DATE_KEY: $DATE_KEY (expected YYYY-MM-DD)" >&2
  exit 1
fi

read -r DEFAULT_START_DATE DEFAULT_END_DATE < <(
  python3 - <<PY
import datetime
d = datetime.date.fromisoformat("${DATE_KEY}")
days_since_sunday = (d.weekday() + 1) % 7   # Monday=0..Sunday=6 -> Sunday anchor
current_sunday = d - datetime.timedelta(days=days_since_sunday)
start = current_sunday - datetime.timedelta(days=7)
end = current_sunday - datetime.timedelta(days=1)
print(start.isoformat(), end.isoformat())
PY
)
START_DATE="${2:-$DEFAULT_START_DATE}"
END_DATE="${3:-$DEFAULT_END_DATE}"

LOG_FILE="$ROOT_DIR/logs/pipeline_${DATE_KEY}.log"

{
  echo "[pipeline] start date_key=$DATE_KEY"
  echo "[pipeline] period=$START_DATE to $END_DATE"

  if [[ "${ENABLE_PREFLIGHT_CHECK:-1}" == "1" ]]; then
    if ! bash "$ROOT_DIR/scripts/preflight_weekly.sh" "$DATE_KEY"; then
      if [[ "${PREFLIGHT_FAIL_OPEN:-0}" == "1" ]]; then
        echo "[pipeline] ⚠️ preflight failed but PREFLIGHT_FAIL_OPEN=1, continuing"
      else
        echo "[pipeline] ❌ preflight failed; aborting (set PREFLIGHT_FAIL_OPEN=1 to continue anyway)" >&2
        exit 1
      fi
    fi
  fi

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

if [[ "${ENABLE_QUALITY_GATE:-1}" == "1" ]]; then
  bash "$ROOT_DIR/scripts/quality_gate_weekly.sh" "$DATE_KEY"
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
