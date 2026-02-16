#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="${LAUNCHD_LABEL:-com.soonho.d2c.weekly}"
WEEKDAY="${LAUNCHD_WEEKDAY:-1}"   # 1=Monday
HOUR="${LAUNCHD_HOUR:-4}"         # 04:00
MINUTE="${LAUNCHD_MINUTE:-0}"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$ROOT_DIR/logs"
OUT_LOG="$LOG_DIR/launchd_weekly.out.log"
ERR_LOG="$LOG_DIR/launchd_weekly.err.log"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>bash '${ROOT_DIR}/scripts/run_weekly.sh'</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${ROOT_DIR}</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>TZ</key>
    <string>Asia/Seoul</string>
  </dict>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key>
    <integer>${WEEKDAY}</integer>
    <key>Hour</key>
    <integer>${HOUR}</integer>
    <key>Minute</key>
    <integer>${MINUTE}</integer>
  </dict>

  <key>RunAtLoad</key>
  <false/>

  <key>StandardOutPath</key>
  <string>${OUT_LOG}</string>
  <key>StandardErrorPath</key>
  <string>${ERR_LOG}</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/${UID}" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/${UID}" "$PLIST_PATH"
launchctl enable "gui/${UID}/${LABEL}"

echo "Installed: $PLIST_PATH"
echo "Schedule: Every Monday ${HOUR}:$(printf '%02d' "$MINUTE") KST"
launchctl print "gui/${UID}/${LABEL}" | sed -n '1,80p'
