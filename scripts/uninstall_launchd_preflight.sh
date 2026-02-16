#!/usr/bin/env bash
set -euo pipefail

LABEL="${LAUNCHD_PREFLIGHT_LABEL:-com.soonho.d2c.weekly.preflight}"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"

launchctl bootout "gui/${UID}" "$PLIST_PATH" >/dev/null 2>&1 || true
rm -f "$PLIST_PATH"

echo "Removed: $PLIST_PATH"
