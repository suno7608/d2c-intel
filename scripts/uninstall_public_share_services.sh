#!/usr/bin/env bash
set -euo pipefail

LABEL_PREFIX="${PUBLIC_SHARE_LABEL_PREFIX:-com.soonho.d2c.public}"
SERVER_LABEL="${LABEL_PREFIX}.server"
TUNNEL_LABEL="${LABEL_PREFIX}.ngrok"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
SERVER_PLIST="$LAUNCH_DIR/${SERVER_LABEL}.plist"
TUNNEL_PLIST="$LAUNCH_DIR/${TUNNEL_LABEL}.plist"

launchctl bootout "gui/${UID}" "$SERVER_PLIST" >/dev/null 2>&1 || true
launchctl bootout "gui/${UID}" "$TUNNEL_PLIST" >/dev/null 2>&1 || true
rm -f "$SERVER_PLIST" "$TUNNEL_PLIST"

echo "Removed services:"
echo "- $SERVER_LABEL"
echo "- $TUNNEL_LABEL"
