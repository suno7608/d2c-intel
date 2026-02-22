#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────────────
# D2C Intel — Monthly Deep Dive Report Build Pipeline
# ──────────────────────────────────────────────────────────────
# Usage: bash scripts/build_publishable_monthly_report.sh [YYYY-MM]
#
# Steps:
#   1. Render Korean HTML (with Chart.js)
#   2. Translate to English
#   3. Render English HTML
#   4. Generate PDF via Playwright
#   5. Copy to latest/ directory
# ──────────────────────────────────────────────────────────────

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
YEAR_MONTH="${1:-$(TZ=Asia/Seoul date +%Y-%m)}"

SRC_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Monthly_Intelligence_${YEAR_MONTH}.md"
OUT_MD_EN="$ROOT_DIR/reports/md/LG_Global_D2C_Monthly_Intelligence_${YEAR_MONTH}_en.md"

OUT_HTML_DIR="$ROOT_DIR/reports/html/monthly/${YEAR_MONTH}"
OUT_HTML="$OUT_HTML_DIR/index.html"
OUT_HTML_EN="$OUT_HTML_DIR/index_en.html"
OUT_PDF_DIR="$ROOT_DIR/reports/pdf"
OUT_PDF="$OUT_PDF_DIR/LG_Global_D2C_Monthly_Intelligence_${YEAR_MONTH}.pdf"
LATEST_DIR="$ROOT_DIR/reports/html/monthly/latest"

mkdir -p "$OUT_HTML_DIR" "$OUT_PDF_DIR" "$LATEST_DIR"

if [ ! -f "$SRC_MD" ]; then
  echo "[monthly-build] ERROR: Source markdown not found: $SRC_MD" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "[monthly-build] node command not found" >&2
  exit 1
fi

echo "[monthly-build] === Building Monthly Report: ${YEAR_MONTH} ==="

# ── Step 1: Render Korean HTML ──
echo "[monthly-build] Step 1: Rendering Korean HTML..."
node --max-old-space-size=4096 "$ROOT_DIR/scripts/render_professional_report.mjs" \
  "$SRC_MD" "$OUT_HTML" "ko"
echo "[monthly-build] ✅ Korean HTML: $OUT_HTML"

# ── Step 2: Translate to English ──
echo "[monthly-build] Step 2: Translating to English..."
if [ -f "$ROOT_DIR/scripts/translate_report_to_english.sh" ]; then
  bash "$ROOT_DIR/scripts/translate_report_to_english.sh" "$SRC_MD" "$OUT_MD_EN"
  echo "[monthly-build] ✅ English markdown: $OUT_MD_EN"
else
  echo "[monthly-build] ⚠️ Translation script not found, skipping English version"
  cp "$SRC_MD" "$OUT_MD_EN"
fi

# ── Step 3: Render English HTML ──
echo "[monthly-build] Step 3: Rendering English HTML..."
node --max-old-space-size=4096 "$ROOT_DIR/scripts/render_professional_report.mjs" \
  "$OUT_MD_EN" "$OUT_HTML_EN" "en"
echo "[monthly-build] ✅ English HTML: $OUT_HTML_EN"

# ── Step 4: Generate PDF ──
echo "[monthly-build] Step 4: Generating PDF..."
if command -v playwright >/dev/null 2>&1; then
  playwright pdf \
    --paper-format A4 \
    --margin "10mm" \
    "file:///$OUT_HTML" "$OUT_PDF" || {
      echo "[monthly-build] ⚠️ PDF generation failed (non-blocking)"
    }
  if [ -f "$OUT_PDF" ]; then
    echo "[monthly-build] ✅ PDF: $OUT_PDF"
  fi
else
  echo "[monthly-build] ⚠️ playwright not found, skipping PDF"
fi

# ── Step 5: Copy to latest/ ──
echo "[monthly-build] Step 5: Updating latest/ directory..."
cp "$OUT_HTML" "$LATEST_DIR/index.html"
cp "$OUT_HTML_EN" "$LATEST_DIR/index_en.html"
if [ -f "$OUT_PDF" ]; then
  cp "$OUT_PDF" "$LATEST_DIR/LG_Global_D2C_Monthly_Intelligence_latest.pdf"
fi

echo "[monthly-build] === Monthly Build Complete: ${YEAR_MONTH} ==="
echo "[monthly-build] KO HTML: $OUT_HTML"
echo "[monthly-build] EN HTML: $OUT_HTML_EN"
if [ -f "$OUT_PDF" ]; then
  echo "[monthly-build] PDF: $OUT_PDF"
fi
