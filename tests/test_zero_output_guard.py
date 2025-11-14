#!/usr/bin/env python3
# this_file: tests/test_zero_output_guard.py

"""Regression tests for zero-output safeguards (Issue #204)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from loguru import logger

from cerebrate_file.cerebrate_file import process_document
from cerebrate_file.cli import run as cli_run
from cerebrate_file.models import Chunk, ChunkDiagnostics, RateLimitStatus


def test_process_document_logs_diagnostics_for_zero_token_chunk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure zero-token chunks emit diagnostics and warnings."""

    chunk = Chunk(text="hello world", token_count=5)
    rate_status = RateLimitStatus(
        requests_remaining=10,
        tokens_remaining=20,
        headers_parsed=True,
    )

    def fake_request(*_args, **_kwargs):
        return "", rate_status

    monkeypatch.setattr("cerebrate_file.cerebrate_file.make_cerebras_request", fake_request)

    captured_messages: list[str] = []

    def _sink(message):
        captured_messages.append(message.record["message"])

    sink_id = logger.add(_sink, level="WARNING")
    try:
        final_output, state = process_document(
            client=object(),
            chunks=[chunk],
            base_prompt="system",
            base_prompt_tokens=5,
            model="zai-glm-4.6",
            temp=0.1,
            top_p=0.9,
            max_tokens_ratio=100,
            sample_size=0,
            metadata=None,
            verbose=False,
            progress_callback=None,
        )
    finally:
        logger.remove(sink_id)

    assert final_output == ""
    assert state.total_output_tokens == 0
    assert len(state.chunk_diagnostics) == 1
    assert state.chunk_diagnostics[0].response_tokens == 0
    assert any("zero tokens" in message for message in captured_messages)


def test_cli_aborts_before_overwriting_when_total_output_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """If the total output tokens are zero the CLI should exit without writing."""

    input_file = tmp_path / "notes.md"
    input_file.write_text("source text", encoding="utf-8")

    diag = ChunkDiagnostics(
        chunk_index=1,
        chunk_tokens=5,
        total_input_tokens=10,
        max_completion_tokens=50,
        response_tokens=0,
        response_chars=0,
        model="zai-glm-4.6",
        temperature=0.7,
        top_p=0.8,
    )
    mocked_state = SimpleNamespace(
        processing_time=0.1,
        chunks_processed=1,
        total_input_tokens=10,
        total_output_tokens=0,
        last_rate_status=SimpleNamespace(headers_parsed=False, requests_remaining=None),
        chunk_diagnostics=[diag],
    )

    stub_chunks = [SimpleNamespace(text="chunk", token_count=5)]

    monkeypatch.setenv("CEREBRAS_API_KEY", "csk-test")

    with (
        patch("cerebrate_file.config.validate_environment"),
        patch("cerebrate_file.chunking.create_chunks", return_value=stub_chunks),
        patch("cerebrate_file.cli.process_document", return_value=("", mocked_state)),
        patch("cerebras.cloud.sdk.Cerebras"),
        patch("cerebrate_file.cli.write_output_atomically") as mock_writer,
    ):
        with pytest.raises(SystemExit) as excinfo:
            cli_run(
                input_data=str(input_file),
                output_data=None,
                verbose=True,
            )

    assert excinfo.value.code == 1
    assert input_file.read_text(encoding="utf-8") == "source text"
    mock_writer.assert_not_called()

    captured = capsys.readouterr()
    assert "zero tokens" in captured.out
