#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LABEL_PREFIX="${PUBLIC_SHARE_LABEL_PREFIX:-com.soonho.d2c.public}"
SERVER_LABEL="${LABEL_PREFIX}.server"
TUNNEL_LABEL="${LABEL_PREFIX}.ngrok"
PORT="${PUBLIC_SHARE_PORT:-8090}"
REPORTS_DIR="$ROOT_DIR/reports"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
SERVER_PLIST="$LAUNCH_DIR/${SERVER_LABEL}.plist"
TUNNEL_PLIST="$LAUNCH_DIR/${TUNNEL_LABEL}.plist"
LOG_DIR="$ROOT_DIR/logs"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/bin/python3}"
NGROK_BIN="${NGROK_BIN:-/opt/homebrew/bin/ngrok}"

mkdir -p "$LAUNCH_DIR" "$LOG_DIR"

cat > "$SERVER_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${SERVER_LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON_BIN}</string>
    <string>-m</string>
    <string>http.server</string>
    <string>${PORT}</string>
    <string>--directory</string>
    <string>${REPORTS_DIR}</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${ROOT_DIR}</string>

  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>${LOG_DIR}/public_server.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/public_server.err.log</string>
</dict>
</plist>
PLIST

cat > "$TUNNEL_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${TUNNEL_LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${NGROK_BIN}</string>
    <string>http</string>
    <string>${PORT}</string>
    <string>--log=stdout</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${ROOT_DIR}</string>

  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>${LOG_DIR}/public_ngrok.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/public_ngrok.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/${UID}" "$SERVER_PLIST" >/dev/null 2>&1 || true
launchctl bootout "gui/${UID}" "$TUNNEL_PLIST" >/dev/null 2>&1 || true

launchctl bootstrap "gui/${UID}" "$SERVER_PLIST"
launchctl bootstrap "gui/${UID}" "$TUNNEL_PLIST"
launchctl enable "gui/${UID}/${SERVER_LABEL}"
launchctl enable "gui/${UID}/${TUNNEL_LABEL}"

URL=""
for i in $(seq 1 30); do
  URL=$(curl -s http://127.0.0.1:4040/api/tunnels | sed -n 's/.*"public_url":"\(https:[^"]*\)".*/\1/p' | head -n1 || true)
  if [[ -n "$URL" ]]; then
    break
  fi
  sleep 1
done

echo "Installed services:"
echo "- $SERVER_LABEL"
echo "- $TUNNEL_LABEL"
echo "Local: http://localhost:${PORT}/html/latest/hub.html"
if [[ -n "$URL" ]]; then
  echo "Public hub: ${URL}/html/latest/hub.html"
else
  echo "Public URL not ready yet. check: launchctl print gui/${UID}/${TUNNEL_LABEL}"
fi
