# this_file: tests/test_compatible.py
"""Explicit providers must preserve identity and fail on unusable completions."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from cerebrate_file.compatible import CompatibleClient, CompletionError


def response(content="Rewritten.", reason="stop"):
    return SimpleNamespace(
        model="actual-model",
        id="req-1",
        usage=None,
        choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=reason)],
    )


def test_complete_when_valid_then_records_requested_and_actual_model():
    sdk = MagicMock()
    sdk.chat.completions.create.return_value = response()
    result = CompatibleClient("requested-model", sdk).complete("Draft", "Rewrite")
    assert result.text == "Rewritten.", "The returned text must be preserved"
    assert result.model == "actual-model", "Actual provider identity must be recorded"
    assert sdk.chat.completions.create.call_args.kwargs["model"] == "requested-model"


@pytest.mark.parametrize(
    ("content", "reason"),
    [("", "stop"), (None, "stop"), ("Partial", "length"), ("Refused", "content_filter")],
)
def test_complete_when_unusable_then_raises_with_retained_text(content, reason):
    sdk = MagicMock()
    sdk.chat.completions.create.return_value = response(content, reason)
    with pytest.raises(CompletionError) as exc:
        CompatibleClient("model", sdk).complete("Draft", "Rewrite")
    assert exc.value.text == (content or ""), "Partial output must remain accessible"


def test_complete_when_raw_prompt_then_uses_completion_endpoint():
    sdk = MagicMock()
    sdk.completions.create.return_value = SimpleNamespace(
        model="model",
        id="req",
        usage=None,
        choices=[SimpleNamespace(text="Result", finish_reason="stop")],
    )
    result = CompatibleClient("model", sdk).complete(
        "Draft", "", raw_prompt="exact prompt", extra_body={"top_k": 0}
    )
    assert result.text == "Result"
    assert sdk.completions.create.call_args.kwargs["prompt"] == "exact prompt"
    sdk.chat.completions.create.assert_not_called()


def test_complete_when_empty_input_then_no_request():
    sdk = MagicMock()
    with pytest.raises(ValueError, match="nonempty text"):
        CompatibleClient("model", sdk).complete(" ", "Rewrite")
    sdk.chat.completions.create.assert_not_called()
