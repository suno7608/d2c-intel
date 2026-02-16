#!/usr/bin/env bash
set -euo pipefail

PROMPT_FILE="$1"
INPUT_REPORT="$2"
OUTPUT_REPORT="$3"
QA_FILE="$4"

if ! command -v claude >/dev/null 2>&1; then
  echo "claude command not found" >> "$QA_FILE"
  cp "$INPUT_REPORT" "$OUTPUT_REPORT"
  exit 0
fi

SYSTEM_PROMPT="$(cat "$PROMPT_FILE")"
REPORT_BODY="$(cat "$INPUT_REPORT")"
FULL_PROMPT="$SYSTEM_PROMPT

[INPUT_REPORT_BEGIN]
$REPORT_BODY
[INPUT_REPORT_END]

위 규칙에 따라 Revised Markdown만 출력하라."

CLAUDE_CMD=(claude -p --output-format text)
if [[ -n "${CLAUDE_MODEL:-}" ]]; then
  CLAUDE_CMD+=(--model "$CLAUDE_MODEL")
fi
CLAUDE_TIMEOUT_SECONDS="${CLAUDE_TIMEOUT_SECONDS:-90}"

TMP_OUT="$(mktemp)"
trap 'rm -f "$TMP_OUT"' EXIT

if perl -e 'alarm shift; exec @ARGV' "$CLAUDE_TIMEOUT_SECONDS" "${CLAUDE_CMD[@]}" "$FULL_PROMPT" > "$TMP_OUT" 2>> "$QA_FILE"; then
  if [[ -s "$TMP_OUT" ]]; then
    cp "$TMP_OUT" "$OUTPUT_REPORT"
    {
      echo
      echo "## Claude CLI Co-work"
      echo "- 상태: 성공"
      echo "- 모델: ${CLAUDE_MODEL:-default}"
    } >> "$QA_FILE"
  else
    cp "$INPUT_REPORT" "$OUTPUT_REPORT"
    {
      echo
      echo "## Claude CLI Co-work"
      echo "- 상태: 빈 출력으로 fallback(copy)"
      echo "- 모델: ${CLAUDE_MODEL:-default}"
    } >> "$QA_FILE"
  fi
else
  cp "$INPUT_REPORT" "$OUTPUT_REPORT"
  {
    echo
    echo "## Claude CLI Co-work"
    echo "- 상태: 실패로 fallback(copy)"
    echo "- 모델: ${CLAUDE_MODEL:-default}"
  } >> "$QA_FILE"
fi
