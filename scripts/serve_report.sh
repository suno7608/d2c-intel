#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${1:-8080}"
BASE_DIR="$ROOT_DIR/reports"

echo "Serving: $BASE_DIR"
echo "Open Main: http://localhost:${PORT}/html/index.html"
echo "Open Hub: http://localhost:${PORT}/html/latest/hub.html"
echo "Open Share: http://localhost:${PORT}/html/latest/share.html"
python3 -m http.server "$PORT" --directory "$BASE_DIR"
