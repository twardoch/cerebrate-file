#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "cerebras-cloud-sdk",
# ]
# ///
# this_file: testapi.py

"""Quick Cerebras streaming smoke-test helper."""

import os
import sys
from pathlib import Path

from cerebras.cloud.sdk import Cerebras


def main() -> int:
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        msg = "Set CEREBRAS_API_KEY in your environment before running."
        print(msg, file=sys.stderr)
        return 1

    changelog_path = Path(__file__).parent / "CHANGELOG.md"
    if not changelog_path.exists():
        print(f"CHANGELOG.md not found at {changelog_path}", file=sys.stderr)
        return 1

    changelog_content = changelog_path.read_text(encoding="utf-8")
    instruction = "Slightly compress this CHANGELOG: only keep relevant facts, eliminate fluff"
    user_message = f"{changelog_content}\n\n{instruction}"

    client = Cerebras(api_key=api_key)

    stream = client.chat.completions.create(
        messages=[
            {"role": "user", "content": user_message},
        ],
        model="zai-glm-4.6",
        stream=True,
        max_completion_tokens=40960,
        temperature=0.99,
        top_p=0.95,
    )

    for chunk in stream:
        # type: ignore
        content = chunk.choices[0].delta.content if chunk.choices else None
        print(content or "", end="", flush=True)

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
