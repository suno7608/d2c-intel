#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/config/pipeline.env"
DATE_KEY="${1:-$(TZ=Asia/Seoul date +%F)}"
LOG_FILE="$ROOT_DIR/logs/preflight_${DATE_KEY}.log"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

ENABLE_PREFLIGHT_OPENCLAW_SMOKE="${ENABLE_PREFLIGHT_OPENCLAW_SMOKE:-0}"
OPENCLAW_SMOKE_TIMEOUT_SECONDS="${OPENCLAW_SMOKE_TIMEOUT_SECONDS:-30}"

mkdir -p "$ROOT_DIR/logs"
: > "$LOG_FILE"

fail_count=0
warn_count=0

ok() {
  echo "[preflight] ✅ $1" | tee -a "$LOG_FILE"
}
warn() {
  warn_count=$((warn_count + 1))
  echo "[preflight] ⚠️ $1" | tee -a "$LOG_FILE"
}
fail() {
  fail_count=$((fail_count + 1))
  echo "[preflight] ❌ $1" | tee -a "$LOG_FILE"
}

summarize_recent_openclaw() {
  python3 - "$ROOT_DIR/logs" <<'PY'
import glob
import json
import os
from collections import Counter

logs_dir = os.path.abspath(__import__("sys").argv[1])
files = sorted(glob.glob(os.path.join(logs_dir, "openclaw_*.diag.jsonl")))[-8:]

if not files:
    print("NO_DATA")
    raise SystemExit(0)

reason_counter = Counter()
attempt_counts = []
elapsed_ms = []

for f in files:
    attempts = 0
    run_elapsed = None
    with open(f, "r", encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue
            event = data.get("event")
            if event == "attempt_result":
                attempts += 1
                reason = data.get("reason", "")
                if reason and reason not in {"success", "quality_fail"}:
                    reason_counter[reason] += 1
            elif event == "run_summary":
                run_elapsed = data.get("total_elapsed_ms")
    if attempts > 0:
        attempt_counts.append(attempts)
    if isinstance(run_elapsed, (int, float)):
        elapsed_ms.append(int(run_elapsed))

if reason_counter:
    top = ", ".join(f"{k}({v})" for k, v in reason_counter.most_common(3))
else:
    top = "none"

avg_attempts = round(sum(attempt_counts) / len(attempt_counts), 2) if attempt_counts else 0
avg_elapsed_sec = round((sum(elapsed_ms) / len(elapsed_ms)) / 1000, 1) if elapsed_ms else 0

print(f"TOP_FAILURES={top}")
print(f"AVG_ATTEMPTS={avg_attempts}")
print(f"AVG_ELAPSED_SEC={avg_elapsed_sec}")
print(f"SAMPLE_RUNS={len(files)}")
PY
}

echo "[preflight] start date=$DATE_KEY" | tee -a "$LOG_FILE"

for cmd in bash python3 jq node openclaw playwright; do
  if command -v "$cmd" >/dev/null 2>&1; then
    ok "command available: $cmd"
  else
    fail "missing command: $cmd"
  fi
done

if [[ -z "${OPENCLAW_RUNNER:-}" ]]; then
  fail "OPENCLAW_RUNNER is empty"
elif [[ ! -x "${OPENCLAW_RUNNER}" ]]; then
  fail "OPENCLAW_RUNNER is not executable: ${OPENCLAW_RUNNER}"
else
  ok "OPENCLAW_RUNNER configured: ${OPENCLAW_RUNNER}"
fi

if [[ "${ENABLE_CLAUDE_COWORK:-1}" == "1" ]]; then
  if [[ -z "${CLAUDE_RUNNER:-}" ]]; then
    fail "CLAUDE_RUNNER is empty while ENABLE_CLAUDE_COWORK=1"
  elif [[ ! -x "${CLAUDE_RUNNER}" ]]; then
    fail "CLAUDE_RUNNER is not executable: ${CLAUDE_RUNNER}"
  else
    ok "CLAUDE_RUNNER configured: ${CLAUDE_RUNNER}"
  fi
fi

if /bin/zsh -lc "launchctl print \"gui/${UID}/ai.openclaw.gateway\" >/dev/null 2>&1"; then
  ok "OpenClaw gateway launch agent is running"
else
  warn "OpenClaw gateway launch agent is not running (may auto-recover)"
fi

if [[ "${ENABLE_OBSIDIAN_EXPORT:-0}" == "1" ]]; then
  if [[ -z "${OBSIDIAN_WEEKLY_ROOT:-}" ]]; then
    fail "OBSIDIAN_WEEKLY_ROOT is empty while ENABLE_OBSIDIAN_EXPORT=1"
  elif [[ ! -d "${OBSIDIAN_WEEKLY_ROOT}" ]]; then
    fail "OBSIDIAN_WEEKLY_ROOT directory not found: ${OBSIDIAN_WEEKLY_ROOT}"
  elif [[ ! -w "${OBSIDIAN_WEEKLY_ROOT}" ]]; then
    fail "OBSIDIAN_WEEKLY_ROOT is not writable: ${OBSIDIAN_WEEKLY_ROOT}"
  else
    ok "Obsidian weekly root writable: ${OBSIDIAN_WEEKLY_ROOT}"
  fi
fi

if [[ "${ENABLE_PREFLIGHT_OPENCLAW_SMOKE}" == "1" ]]; then
  ok "running optional OpenClaw smoke check (${OPENCLAW_SMOKE_TIMEOUT_SECONDS}s)"
  if perl -e 'my $t=shift @ARGV; local $SIG{ALRM}=sub{exit 124}; alarm $t; my $rc=system @ARGV; alarm 0; exit($rc == -1 ? 125 : ($rc >> 8));' \
      "$OPENCLAW_SMOKE_TIMEOUT_SECONDS" \
      openclaw agent --agent "${OPENCLAW_AGENT_ID:-main}" --local --json --timeout "$OPENCLAW_SMOKE_TIMEOUT_SECONDS" \
      --message "Reply JSON only: {\"ok\":true}" >/dev/null 2>>"$LOG_FILE"; then
    ok "OpenClaw smoke check passed"
  else
    warn "OpenClaw smoke check failed/timed out"
  fi
else
  ok "OpenClaw smoke check skipped (ENABLE_PREFLIGHT_OPENCLAW_SMOKE=0)"
fi

recent_summary="$(summarize_recent_openclaw || true)"
if [[ "$recent_summary" == "NO_DATA" ]] || [[ -z "$recent_summary" ]]; then
  warn "no recent OpenClaw diagnostic logs yet (openclaw_*.diag.jsonl)"
else
  top_failures="$(echo "$recent_summary" | awk -F= '/^TOP_FAILURES=/{print $2}')"
  avg_attempts="$(echo "$recent_summary" | awk -F= '/^AVG_ATTEMPTS=/{print $2}')"
  avg_elapsed="$(echo "$recent_summary" | awk -F= '/^AVG_ELAPSED_SEC=/{print $2}')"
  sample_runs="$(echo "$recent_summary" | awk -F= '/^SAMPLE_RUNS=/{print $2}')"
  ok "recent OpenClaw top failures: ${top_failures:-none}"
  ok "recent OpenClaw avg retries: ${avg_attempts:-0} (sample runs: ${sample_runs:-0})"
  ok "recent OpenClaw avg total time: ${avg_elapsed:-0}s"
fi

if [[ -f "$ROOT_DIR/logs/openclaw_adaptive_policy.env" ]]; then
  # shellcheck disable=SC1090
  source "$ROOT_DIR/logs/openclaw_adaptive_policy.env"
  ok "adaptive policy state: reason=${LAST_REASON:-none}, level=${LEVEL:-0}, updated=${UPDATED_DATE:-unknown}"
else
  warn "adaptive policy file missing (will be created after first failure pattern)"
fi

if [[ "$fail_count" -gt 0 ]]; then
  echo "[preflight] failed ($fail_count fail, $warn_count warn) log=$LOG_FILE" | tee -a "$LOG_FILE"
  exit 1
fi

echo "[preflight] passed ($warn_count warn) log=$LOG_FILE" | tee -a "$LOG_FILE"
