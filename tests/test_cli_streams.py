#!/usr/bin/env python3
# this_file: tests/test_cli_streams.py

"""CLI streaming tests for stdin/stdout support."""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from cerebrate_file.cli import run as cli_run


@pytest.fixture
def stubbed_chunks() -> list:
    """Provide a minimal chunk list used by the CLI during streaming tests."""
    return [SimpleNamespace(text="chunk content", token_count=5)]


def _stub_state() -> SimpleNamespace:
    """Create a minimal processing state object for mocks."""
    return SimpleNamespace(
        processing_time=0.1,
        chunks_processed=1,
        total_input_tokens=5,
        total_output_tokens=7,
        last_rate_status=SimpleNamespace(headers_parsed=False, requests_remaining=None),
        chunk_diagnostics=[],
    )


def test_cli_run_streams_stdin_to_stdout(
    monkeypatch: pytest.MonkeyPatch, stubbed_chunks: list, capsys: pytest.CaptureFixture[str]
) -> None:
    """Running with input_data='-' and output_data='-' should pipe stdin through the pipeline."""
    # Provide stdin data
    monkeypatch.setattr("sys.stdin", io.StringIO("# title\n\nbody text"))

    with (
        patch("cerebrate_file.config.validate_environment"),
        patch("cerebrate_file.chunking.create_chunks", return_value=stubbed_chunks),
        patch(
            "cerebrate_file.cli.process_document",
            return_value=(
                "Transformed body",
                _stub_state(),
            ),
        ),
        patch("cerebras.cloud.sdk.Cerebras"),
    ):
        cli_run(
            input_data="-",
            output_data="-",
            verbose=False,
            dry_run=False,
        )

    captured = capsys.readouterr()
    assert captured.out == "Transformed body", "stdout should contain only the transformed output"
    assert captured.err == "", (
        "stderr capture should be empty because streaming logs route to the real stderr"
    )
