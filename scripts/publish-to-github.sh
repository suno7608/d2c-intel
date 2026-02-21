#!/usr/bin/env bash
set -euo pipefail

# D2C Intel 리포트를 GitHub Pages로 발행
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
D2C_DIR="$HOME/Documents/New project/d2c-intel"
GH_REPO="/tmp/d2c-weekly-intel"

echo "[publish] Syncing reports to GitHub repo..."

# latest hub
cp "$D2C_DIR/reports/html/latest/hub.html" "$GH_REPO/reports/html/latest/"
cp "$D2C_DIR/reports/html/latest/hub_en.html" "$GH_REPO/reports/html/latest/" 2>/dev/null || true

# manifest
cp "$D2C_DIR/reports/html/manifest.json" "$GH_REPO/reports/html/"

# 주차별 HTML 폴더 (새로운 것만)
for dir in "$D2C_DIR"/reports/html/2026-*/; do
  week=$(basename "$dir")
  if [ ! -d "$GH_REPO/reports/html/$week" ]; then
    cp -r "$dir" "$GH_REPO/reports/html/$week"
    echo "[publish] Added $week"
  fi
done

# PDF
cp "$D2C_DIR"/reports/pdf/*.pdf "$GH_REPO/reports/html/pdf/" 2>/dev/null || true

# MD (최종본만)
for f in "$D2C_DIR"/reports/md/*_R2_16country.md "$D2C_DIR"/reports/md/*_en.md; do
  [ -f "$f" ] && cp "$f" "$GH_REPO/reports/html/md/"
done

# git push
cd "$GH_REPO"
git add -A
if git diff --staged --quiet; then
  echo "[publish] No changes to push"
  exit 0
fi
git commit -m "📊 D2C Weekly Intel update $(TZ=Asia/Seoul date +%F)"
git push
echo "[publish] Done!"
