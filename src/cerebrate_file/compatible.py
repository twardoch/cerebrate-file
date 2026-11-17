# this_file: src/cerebrate_file/compatible.py
"""Explicit OpenAI-compatible requests without retries or model fallback.

Callers own retry policy and document persistence. This boundary records provider
identity and retains partial text when a response cannot count as complete.
"""

from dataclasses import dataclass
from typing import Any

from openai import OpenAI


@dataclass(frozen=True)
class Completion:
    """A completed response with provider provenance."""

    text: str
    model: str
    request_id: str
    finish_reason: str
    usage: dict[str, Any]


class CompletionError(RuntimeError):
    """An unusable response, retaining partial output for inspection."""

    def __init__(self, message: str, text: str = "") -> None:
        super().__init__(message)
        self.text = text


class CompatibleClient:
    """Select one model at one endpoint; never substitute another model."""

    def __init__(self, model: str, client: Any) -> None:
        if not model.strip():
            raise ValueError("model must not be empty")
        self.model = model
        self.client = client

    @classmethod
    def connect(
        cls, model: str, base_url: str, api_key: str, timeout: float = 180.0
    ) -> "CompatibleClient":
        """Build an SDK client with explicit timeout and disabled SDK retries."""
        if not api_key or not base_url or timeout <= 0:
            raise ValueError("api_key, base_url and positive timeout are required")
        return cls(
            model, OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=0)
        )

    def complete(
        self,
        text: str,
        instruction: str,
        *,
        continuity: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.3,
        top_p: float = 0.9,
        raw_prompt: str | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> Completion:
        """Request chat or exact raw completion; reject missing/truncated text."""
        if not text.strip() or max_tokens <= 0:
            raise ValueError("nonempty text and positive max_tokens are required")
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
        }
        if extra_body:
            params["extra_body"] = extra_body
        if raw_prompt is not None:
            response = self.client.completions.create(prompt=raw_prompt, **params)
        else:
            system = instruction + ("\n\n" + continuity if continuity else "")
            response = self.client.chat.completions.create(
                messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
                **params,
            )
        if not response.choices:
            raise CompletionError("Response has no choices")
        choice = response.choices[0]
        result = (choice.text if raw_prompt is not None else choice.message.content) or ""
        if not isinstance(result, str):
            raise CompletionError("Response text must be a string")
        reason = choice.finish_reason
        if not result.strip() or reason != "stop":
            raise CompletionError(f"Unusable completion: finish_reason={reason}", result)
        usage = response.usage.model_dump() if response.usage is not None else {}
        return Completion(result, response.model, response.id, reason, usage)
