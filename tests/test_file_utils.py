#!/usr/bin/env python3
# this_file: tests/test_file_utils.py

"""Unit tests for file utility helpers."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pytest

from cerebrate_file.file_utils import read_file_safely, write_output_atomically


@pytest.fixture
def temporary_text_file() -> Path:
    """Provide a temporary UTF-8 text file with sample content."""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as handle:
        handle.write("Sample text file content.")
        temp_path = Path(handle.name)
    yield temp_path
    if temp_path.exists():
        temp_path.unlink()


def test_read_file_safely_when_path_dash_reads_from_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    """`read_file_safely('-')` should consume stdin instead of touching the filesystem."""
    fake_stdin = io.StringIO("Streamed input from stdin.\n")
    monkeypatch.setattr("sys.stdin", fake_stdin)

    result = read_file_safely("-")

    assert result == "Streamed input from stdin.\n", "stdin content should be returned verbatim"


def test_write_output_atomically_when_path_dash_writes_to_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`write_output_atomically` should stream to stdout when given '-' as the destination."""
    fake_stdout = io.StringIO()
    monkeypatch.setattr("sys.stdout", fake_stdout)

    write_output_atomically("Output via stdout", "-")

    assert fake_stdout.getvalue() == "Output via stdout", (
        "stdout should receive the written content"
    )


def test_write_output_atomically_when_path_dash_preserves_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Frontmatter metadata should still wrap content when streaming to stdout."""
    fake_stdout = io.StringIO()
    monkeypatch.setattr("sys.stdout", fake_stdout)

    write_output_atomically("Body", "-", {"title": "Demo"})

    captured = fake_stdout.getvalue()
    assert captured.startswith("---\n"), "Frontmatter header should be emitted"
    assert "title: Demo" in captured, "Metadata fields must be present"
    assert captured.rstrip().endswith("Body"), "Content should follow metadata"


def test_read_file_safely_reads_regular_files(temporary_text_file: Path) -> None:
    """Ensure existing behaviour for filesystem paths still works."""
    assert read_file_safely(str(temporary_text_file)).startswith("Sample text"), (
        "File path reading must remain intact"
    )


def test_write_output_atomically_writes_regular_files(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure file-system writes still occur for real paths."""
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        output_path = Path(handle.name)

    try:
        write_output_atomically("Persistent content", output_path)
        assert output_path.read_text(encoding="utf-8") == "Persistent content"
    finally:
        if output_path.exists():
            output_path.unlink()
