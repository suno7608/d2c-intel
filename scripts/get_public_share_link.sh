#!/usr/bin/env bash
set -euo pipefail

PORT="${PUBLIC_SHARE_PORT:-8090}"
URL=$(curl -s http://127.0.0.1:4040/api/tunnels | sed -n 's/.*"public_url":"\(https:[^"]*\)".*/\1/p' | head -n1 || true)

echo "Local hub: http://localhost:${PORT}/html/latest/hub.html"
if [[ -n "$URL" ]]; then
  echo "Public hub: ${URL}/html/latest/hub.html"
  echo "Public week report: ${URL}/html/latest/index.html"
  echo "$URL" > "/Users/soonho/Documents/New project/d2c-intel/logs/latest_public_url.txt"
else
  echo "Public URL not found. check ngrok service status." >&2
  exit 1
fi
