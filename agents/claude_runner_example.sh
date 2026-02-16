#!/usr/bin/env bash
set -euo pipefail

# Args:
# 1) prompt file
# 2) input report
# 3) output report
# 4) qa summary file
PROMPT_FILE="$1"
INPUT_REPORT="$2"
OUTPUT_REPORT="$3"
QA_FILE="$4"

# TODO: 실제 Claude Code/Claude CLI 호출로 교체
# 환경마다 CLI 문법이 달라 placeholder로 제공
# 예시 흐름:
# cat "$PROMPT_FILE" "$INPUT_REPORT" | claude <flags> > "$OUTPUT_REPORT"

cp "$INPUT_REPORT" "$OUTPUT_REPORT"

{
  echo
  echo "## Example Claude Runner Result"
  echo "- Prompt file: \`$PROMPT_FILE\`"
  echo "- Input report: \`$INPUT_REPORT\`"
  echo "- Output report: \`$OUTPUT_REPORT\`"
  echo "- 상태: 실제 Claude 호출 없이 copy 처리"
} >> "$QA_FILE"
