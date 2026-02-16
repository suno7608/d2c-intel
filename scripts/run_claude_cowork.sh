#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATE_KEY="${1:-$(TZ=Asia/Seoul date +%F)}"
INPUT_REPORT="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}.md"
PROMPT_FILE="$ROOT_DIR/prompts/claude_cowork_review.md"
OUTPUT_REPORT="$ROOT_DIR/reports/md/LG_Global_D2C_Weekly_Intelligence_${DATE_KEY}_claude.md"
QA_FILE="$ROOT_DIR/qa/qa_summary_${DATE_KEY}.md"

mkdir -p "$ROOT_DIR/qa" "$ROOT_DIR/reports/md"

if [[ ! -f "$INPUT_REPORT" ]]; then
  echo "input report not found: $INPUT_REPORT" >&2
  exit 1
fi

cat > "$QA_FILE" <<EOF2
# QA Summary (${DATE_KEY})

## Co-work Status
- Claude Co-work enabled: ${ENABLE_CLAUDE_COWORK:-1}
- External runner configured: $([[ -n "${CLAUDE_RUNNER:-}" ]] && echo "yes" || echo "no")

## Link Format Rule
- Required: [🔗 Source](actual_URL_here)
- Missing URL fallback: ❓[출처 미확인 — 검색어: "..."]

## Findings
- (자동/수동 검토 결과를 여기에 누적)
EOF2

if [[ "${ENABLE_CLAUDE_COWORK:-1}" != "1" ]]; then
  cp "$INPUT_REPORT" "$OUTPUT_REPORT"
  echo "claude co-work disabled; copied original report"
  exit 0
fi

if [[ -n "${CLAUDE_RUNNER:-}" ]]; then
  "$CLAUDE_RUNNER" "$PROMPT_FILE" "$INPUT_REPORT" "$OUTPUT_REPORT" "$QA_FILE"
  echo "claude co-work completed: $OUTPUT_REPORT"
else
  cp "$INPUT_REPORT" "$OUTPUT_REPORT"
  {
    echo
    echo "## Manual Step Required"
    echo "- CLAUDE_RUNNER가 설정되지 않아 자동 리뷰를 건너뛰었습니다."
    echo "- 아래 입력을 Claude Code/Claude Co-work에 전달해 리뷰를 수행하세요."
    echo "  - Prompt: \`$PROMPT_FILE\`"
    echo "  - Input Report: \`$INPUT_REPORT\`"
    echo "  - Output Report(제안): \`$OUTPUT_REPORT\`"
  } >> "$QA_FILE"
  echo "claude runner missing; fallback copy created"
fi
