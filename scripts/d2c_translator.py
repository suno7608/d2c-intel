#!/usr/bin/env python3
"""
D2C Intel — Claude API Translator (Sonnet 4.5)
================================================
translate_report_to_english.sh의 CLAUDE_TRANSLATE_RUNNER로 사용됩니다.
Anthropic API를 통해 Claude Sonnet 4.5로 한→영 번역을 수행합니다.

Usage (standalone):
    python scripts/d2c_translator.py <prompt_file> <source_md> <output_md>

Usage (via translate_report_to_english.sh):
    CLAUDE_TRANSLATE_RUNNER="python3 scripts/d2c_translator.py"

Environment:
    ANTHROPIC_API_KEY        — Anthropic API key (required)
    CLAUDE_MODEL_TRANSLATE   — 모델 지정 (default: claude-sonnet-4-5-20250929)
"""

import os
import sys
from pathlib import Path

import anthropic

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: d2c_translator.py <prompt_file> <source_md> <output_md>",
            file=sys.stderr,
        )
        sys.exit(1)

    prompt_file = Path(sys.argv[1])
    source_md = Path(sys.argv[2])
    output_md = Path(sys.argv[3])

    # Validate inputs
    if not prompt_file.exists():
        print(f"Prompt file not found: {prompt_file}", file=sys.stderr)
        sys.exit(1)
    if not source_md.exists():
        print(f"Source markdown not found: {source_md}", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    model = os.environ.get("CLAUDE_MODEL_TRANSLATE", DEFAULT_MODEL)

    # Read inputs
    system_prompt = prompt_file.read_text(encoding="utf-8")
    report_body = source_md.read_text(encoding="utf-8")

    user_prompt = f"""{system_prompt}

[INPUT_MARKDOWN_BEGIN]
{report_body}
[INPUT_MARKDOWN_END]

Output markdown only."""

    # Call Claude API
    print(f"Translating with {model}...", file=sys.stderr)
    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=16000,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as e:
        print(f"Claude API error: {e}", file=sys.stderr)
        sys.exit(1)

    content = response.content[0].text if response.content else ""
    usage = response.usage

    if not content.strip():
        print("Empty response from Claude", file=sys.stderr)
        sys.exit(1)

    # Clean markdown wrappers
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # Write output
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(text.strip() + "\n", encoding="utf-8")

    print(
        f"Translation complete: {output_md.name} "
        f"(input={usage.input_tokens}, output={usage.output_tokens})",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
