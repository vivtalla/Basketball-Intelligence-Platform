"""Run the slop-review prompt against a PR diff via the Anthropic API.

Used by `.github/workflows/slop-review.yml`. Reads:
- PR diff from stdin (or `--diff-file`)
- Changed-file list from `--files-file`
- Commit messages from `--commits-file`

Calls Claude with the canonical prompt in `qa/slop-review-prompt.md` as a
cached system prompt (so repeated PRs share the cache). Prints the
review markdown to stdout for the GitHub Action to post as a PR comment.

Requires ANTHROPIC_API_KEY in env.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from anthropic import Anthropic

MODEL = os.environ.get("SLOP_REVIEW_MODEL", "claude-sonnet-4-6")
PROMPT_PATH = Path(__file__).parent / "slop-review-prompt.md"

# Cap diff size to keep cost predictable. Larger diffs get truncated with
# a marker so the reviewer still sees the structure.
MAX_DIFF_CHARS = 80_000


def read_file(path: str, max_chars: int = 0) -> str:
    raw = Path(path).read_text(encoding="utf-8")
    if max_chars and len(raw) > max_chars:
        return raw[:max_chars] + f"\n\n[TRUNCATED: {len(raw) - max_chars} chars omitted]\n"
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diff-file", required=True, help="Path to PR diff")
    parser.add_argument("--files-file", required=True, help="Path to newline-separated list of changed files")
    parser.add_argument("--commits-file", required=True, help="Path to commit messages")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 2

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    diff = read_file(args.diff_file, max_chars=MAX_DIFF_CHARS)
    files = read_file(args.files_file)
    commits = read_file(args.commits_file)

    if not diff.strip() or not files.strip():
        print("No code changes to review — skipping.")
        return 0

    user_message = (
        f"<files>\n{files}\n</files>\n\n"
        f"<commits>\n{commits}\n</commits>\n\n"
        f"<diff>\n{diff}\n</diff>\n\n"
        "Run the slop-review checkpoints against this PR and emit the report."
    )

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    output = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    print(output)

    # Surface cache hit-rate to the workflow log so we can monitor cost.
    usage = response.usage
    print(
        f"\n\n<!-- api usage: input={usage.input_tokens} "
        f"cache_read={getattr(usage, 'cache_read_input_tokens', 0)} "
        f"cache_creation={getattr(usage, 'cache_creation_input_tokens', 0)} "
        f"output={usage.output_tokens} -->",
        file=sys.stderr,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
