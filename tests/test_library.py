# this_file: tests/test_library.py
"""Public library API tests without remote calls."""

from unittest.mock import patch

import pytest

from cerebrate_file import process_file, process_text
from cerebrate_file.askllm2 import AskLLM2Client
from cerebrate_file.models import RateLimitStatus


def test_process_text_uses_default_chain_and_preserves_roles():
    with patch.object(AskLLM2Client, "complete", return_value="Corrected.") as call:
        result = process_text("Original.", "Correct grammar.", provider="askllm2")
    assert result == "Corrected."
    messages = call.call_args.args[0]
    assert messages[0] == {"role": "system", "content": "Correct grammar."}
    assert messages[1]["role"] == "user"
    assert "Original." in messages[1]["content"]


def test_process_text_raises_instead_of_returning_error_marker(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")
    with (
        patch("cerebrate_file.library.Cerebras"),
        patch(
            "cerebrate_file.cerebrate_file.make_request_with_fallback",
            side_effect=RuntimeError("failure"),
        ),
        pytest.raises(RuntimeError, match="failure"),
    ):
        process_text("Original.", "Edit.")


def test_process_text_preserves_original_exception(monkeypatch):
    class ProviderError(Exception):
        def __init__(self, message, *, code):
            super().__init__(message)
            self.code = code

    monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")
    with (
        patch("cerebrate_file.library.Cerebras"),
        patch(
            "cerebrate_file.cerebrate_file.make_request_with_fallback",
            side_effect=ProviderError("failure", code=401),
        ),
        pytest.raises(ProviderError, match="failure") as captured,
    ):
        process_text("Original.", "Edit.")
    assert captured.value.code == 401


def test_askllm2_engine_preserves_original_exception():
    from cerebrate_file.cerebrate_file import process_document
    from cerebrate_file.models import Chunk

    class ProviderError(Exception):
        def __init__(self, message, *, code):
            super().__init__(message)
            self.code = code

    client = AskLLM2Client("auto")
    with (
        patch.object(client, "complete", side_effect=ProviderError("failure", code=401)),
        pytest.raises(ProviderError, match="failure") as captured,
    ):
        process_document(client, [Chunk("text", 1)], "edit", 1, "auto", 0.5, 0.9, 100, 0)
    assert captured.value.code == 401


def test_process_text_rejects_empty_model_result(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")
    with (
        patch("cerebrate_file.library.Cerebras"),
        patch(
            "cerebrate_file.cerebrate_file.make_request_with_fallback",
            return_value=("", RateLimitStatus(), "test"),
        ),
        pytest.raises(ValueError, match="empty response"),
    ):
        process_text("Original.", "Edit.")


def test_process_file_preserves_original_when_request_fails(tmp_path):
    path = tmp_path / "input.md"
    path.write_text("Keep this.")
    with (
        patch("cerebrate_file.library.process_text", side_effect=RuntimeError("failure")),
        pytest.raises(RuntimeError, match="failure"),
    ):
        process_file(path, "Edit.", output_path=path)
    assert path.read_text() == "Keep this."


def test_process_file_returns_text_and_preserves_mode_when_replacing(tmp_path):
    path = tmp_path / "input.md"
    path.write_text("Original.")
    path.chmod(0o640)
    with patch("cerebrate_file.library.process_text", return_value="Edited."):
        assert process_file(path, "Edit.", output_path=path) == "Edited."
    assert path.read_text() == "Edited."
    assert path.stat().st_mode & 0o777 == 0o640


def test_process_text_validates_options_without_network():
    with pytest.raises(ValueError, match="provider"):
        process_text("x", "edit", provider="unknown")
    with pytest.raises(ValueError, match="chunk_size"):
        process_text("x", "edit", chunk_size=0)
    assert process_text("", "edit") == ""


@pytest.mark.parametrize("data_format", ["markdown", "semantic"])
def test_multiple_chunks_preserve_input_whitespace_with_identity_model(data_format):
    text = "Alpha one.\n\nBeta two.\n\nGamma three.\n"
    with patch.object(
        AskLLM2Client, "complete", side_effect=lambda messages, *_: messages[1]["content"]
    ):
        result = process_text(
            text,
            "Copy exactly.",
            provider="askllm2",
            data_format=data_format,
            chunk_size=4,
            sample_size=0,
        )
    assert result == text


def test_process_file_rejects_truncated_cerebras_output(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock

    path = tmp_path / "input.md"
    path.write_text("Original file.")
    monkeypatch.setenv("CEREBRAS_API_KEY", "test-key")
    client = Mock()
    client.chat.completions.create.return_value = [
        SimpleNamespace(
            choices=[
                SimpleNamespace(delta=SimpleNamespace(content="partial"), finish_reason="length")
            ]
        )
    ]
    with (
        patch("cerebrate_file.library.Cerebras", return_value=client),
        pytest.raises(ValueError, match="Incomplete Cerebras response"),
    ):
        process_file(path, "Edit.", output_path=path)
    assert path.read_text() == "Original file."
