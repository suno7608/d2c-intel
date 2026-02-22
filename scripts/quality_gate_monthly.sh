#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────────────────
# D2C Intel — Monthly Quality Gate
# ──────────────────────────────────────────────────────────────
# Usage: bash scripts/quality_gate_monthly.sh [YYYY-MM]
# ──────────────────────────────────────────────────────────────

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
YEAR_MONTH="${1:-$(TZ=Asia/Seoul date +%Y-%m)}"

echo "[quality-monthly] start month=${YEAR_MONTH}"

ISSUES=0

check() {
  local desc="$1"
  local ok="$2"
  if [ "$ok" = "true" ]; then
    echo "[quality-monthly] ✅ $desc"
  else
    echo "[quality-monthly] ❌ $desc"
    ISSUES=$((ISSUES + 1))
  fi
}

# ── File existence checks ──
MERGED_JSONL="$ROOT_DIR/data/monthly_raw/openclaw_${YEAR_MONTH}_merged.jsonl"
MONTHLY_STATS="$ROOT_DIR/data/monthly_stats/${YEAR_MONTH}.json"
SRC_MD="$ROOT_DIR/reports/md/LG_Global_D2C_Monthly_Intelligence_${YEAR_MONTH}.md"
KO_HTML="$ROOT_DIR/reports/html/monthly/${YEAR_MONTH}/index.html"
EN_HTML="$ROOT_DIR/reports/html/monthly/${YEAR_MONTH}/index_en.html"

check "exists: merged JSONL" "$([ -f "$MERGED_JSONL" ] && echo true || echo false)"
check "exists: monthly stats" "$([ -f "$MONTHLY_STATS" ] && echo true || echo false)"
check "exists: Korean markdown" "$([ -f "$SRC_MD" ] && echo true || echo false)"
check "exists: Korean HTML" "$([ -f "$KO_HTML" ] && echo true || echo false)"
check "exists: English HTML" "$([ -f "$EN_HTML" ] && echo true || echo false)"

# ── Data quality checks ──
if [ -f "$MONTHLY_STATS" ] && command -v jq >/dev/null 2>&1; then
  TOTAL_RECORDS=$(jq -r '.total_records // 0' "$MONTHLY_STATS")
  WEEKS_COUNT=$(jq -r '.weeks_count // 0' "$MONTHLY_STATS")
  COUNTRIES_COUNT=$(jq -r '.countries_count // 0' "$MONTHLY_STATS")
  TV_RATIO=$(jq -r '.tv_ratio_pct // 0' "$MONTHLY_STATS")

  MIN_RECORDS=${MIN_MONTHLY_RECORDS:-800}
  MIN_WEEKS=${MIN_WEEKLY_REPORTS:-2}
  MIN_COUNTRIES=${MIN_MONTHLY_COUNTRIES:-12}
  MAX_TV_RATIO=${MAX_MONTHLY_TV_RATIO:-45}

  check "record count $TOTAL_RECORDS >= $MIN_RECORDS" \
    "$([ "$TOTAL_RECORDS" -ge "$MIN_RECORDS" ] && echo true || echo false)"
  check "weeks count $WEEKS_COUNT >= $MIN_WEEKS" \
    "$([ "$WEEKS_COUNT" -ge "$MIN_WEEKS" ] && echo true || echo false)"
  check "country count $COUNTRIES_COUNT >= $MIN_COUNTRIES" \
    "$([ "$COUNTRIES_COUNT" -ge "$MIN_COUNTRIES" ] && echo true || echo false)"
  check "tv ratio ${TV_RATIO}% <= ${MAX_TV_RATIO}%" \
    "$(echo "$TV_RATIO $MAX_TV_RATIO" | awk '{print ($1 <= $2) ? "true" : "false"}')"

  # Product breakdown
  for product in TV Refrigerator "Washing Machine" Monitor "LG gram"; do
    key=$(echo "$product" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')
    count=$(jq -r ".products.\"$product\" // 0" "$MONTHLY_STATS")
    echo "[quality-monthly] ℹ️ $product: $count records"
  done
fi

# ── Markdown quality checks ──
if [ -f "$SRC_MD" ]; then
  MD_SIZE=$(wc -c < "$SRC_MD" | tr -d ' ')
  MD_SIZE_KB=$((MD_SIZE / 1024))
  check "markdown size ${MD_SIZE_KB}KB >= 80KB" \
    "$([ "$MD_SIZE_KB" -ge 80 ] && echo true || echo false)"

  INSIGHT_COUNT=$(grep -c "### 핵심 인사이트" "$SRC_MD" || echo 0)
  ACTION_COUNT=$(grep -c "### 실행 필요" "$SRC_MD" || echo 0)
  check "핵심 인사이트 blocks $INSIGHT_COUNT >= 6" \
    "$([ "$INSIGHT_COUNT" -ge 6 ] && echo true || echo false)"
  check "실행 필요 blocks $ACTION_COUNT >= 6" \
    "$([ "$ACTION_COUNT" -ge 6 ] && echo true || echo false)"

  SOURCE_LINKS=$(grep -oP "\[🔗[^\]]*\]\(https?://" "$SRC_MD" | wc -l | tr -d ' ')
  check "source links $SOURCE_LINKS >= 15" \
    "$([ "$SOURCE_LINKS" -ge 15 ] && echo true || echo false)"

  CHART_MARKERS=$(grep -cP "<!-- CHART:\w+ -->" "$SRC_MD" || echo 0)
  check "chart markers $CHART_MARKERS >= 3" \
    "$([ "$CHART_MARKERS" -ge 3 ] && echo true || echo false)"

  # No placeholders
  if grep -qP "(TODO|TBD|작성 ?중|PLACEHOLDER)" "$SRC_MD"; then
    check "no placeholder records in markdown" "false"
  else
    check "no placeholder records in markdown" "true"
  fi
fi

# ── English HTML quality ──
if [ -f "$EN_HTML" ]; then
  if grep -qP "[가-힣]" "$EN_HTML"; then
    check "no Hangul in English HTML" "false"
  else
    check "no Hangul in English HTML" "true"
  fi
fi

# ── Summary ──
if [ "$ISSUES" -gt 0 ]; then
  echo "[quality-monthly] failed with $ISSUES issue(s)"
  exit 1
else
  echo "[quality-monthly] all checks passed"
fi
