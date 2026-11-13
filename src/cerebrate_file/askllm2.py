# this_file: src/cerebrate_file/askllm2.py
"""Send document chunks to the user's unified LLM command."""

import json
import subprocess
from pathlib import Path
from typing import Any


class AskLLM2Client:
    """Invoke askllm2 with document text on stdin, keeping it out of argv."""

    def __init__(self, model: str) -> None:
        self.model = model

    def complete(
        self, messages: list[dict[str, str]], max_tokens: int, temperature: float, top_p: float
    ) -> str:
        prompt = json.dumps(messages, ensure_ascii=False)
        command = [
            str(Path.home() / "bin" / "askllm2.py"),
            "--messages",
            "-",
            "--model",
            self.model,
            "--max_tokens",
            str(max_tokens),
            "--temperature",
            str(temperature),
            "--top_p",
            str(top_p),
        ]
        try:
            result = subprocess.run(
                command, input=prompt, text=True, capture_output=True, timeout=300, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("askllm2 could not complete the request") from exc
        if result.returncode:
            raise RuntimeError(f"askllm2 failed with exit status {result.returncode}")
        if not result.stdout.strip():
            raise RuntimeError("askllm2 returned an empty response")
        return result.stdout.removesuffix("\n")

    def explain_metadata(
        self, existing: dict[str, Any], text: str, temp: float, top_p: float
    ) -> dict[str, Any]:
        prompt = (
            "Fill missing metadata fields from the text. Return only a JSON object.\n"
            f"Existing metadata: {json.dumps(existing, default=str)}\nText: {text[:4000]}"
        )
        result = json.loads(self.complete([{"role": "user", "content": prompt}], 4096, temp, top_p))
        if not isinstance(result, dict):
            raise ValueError("askllm2 metadata response must be a JSON object")
        return result
