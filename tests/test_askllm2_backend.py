# this_file: tests/test_askllm2_backend.py
"""The unified backend forwards chunks without exposing text in argv."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from cerebrate_file.askllm2 import AskLLM2Client
from cerebrate_file.cli import run
from cerebrate_file.models import Chunk


def test_askllm2_passes_prompt_on_stdin_and_generation_options():
    client = AskLLM2Client("poe:Gemma")
    with patch("cerebrate_file.askllm2.subprocess.run") as mock:
        mock.return_value = SimpleNamespace(returncode=0, stdout="rewritten\n")
        result = client.complete(
            [{"role": "system", "content": "rewrite"}, {"role": "user", "content": "private text"}],
            123,
            0.2,
            0.8,
        )
    command = mock.call_args.args[0]
    assert result == "rewritten"
    assert json.loads(mock.call_args.kwargs["input"]) == [
        {"role": "system", "content": "rewrite"},
        {"role": "user", "content": "private text"},
    ]
    assert command[1:3] == ["--messages", "-"]
    assert "private text" not in command
    assert command[-6:] == ["--max_tokens", "123", "--temperature", "0.2", "--top_p", "0.8"]


@pytest.mark.parametrize("output_data", [None, "existing"])
def test_askllm2_failure_preserves_files(tmp_path: Path, monkeypatch, output_data):
    input_file = tmp_path / "input.md"
    input_file.write_text("original")
    output_file = tmp_path / "output.md"
    output_file.write_text("existing")
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    monkeypatch.setattr(
        "cerebrate_file.cli.create_chunks", lambda *_: [Chunk("one", 1), Chunk("two", 1)]
    )
    with (
        patch.object(AskLLM2Client, "complete", side_effect=["rewritten", RuntimeError("failed")]),
        pytest.raises(RuntimeError, match="failed"),
    ):
        run(
            str(input_file),
            str(output_file) if output_data else None,
            provider="askllm2",
            force=True,
            verbose=True,
        )
    assert input_file.read_text() == "original"
    assert output_file.read_text() == "existing"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["input.md", "output.md"]


def test_askllm2_success_writes_output_without_cerebras_key(tmp_path: Path, monkeypatch):
    input_file = tmp_path / "input.md"
    input_file.write_text("original")
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    with patch.object(AskLLM2Client, "complete", return_value="rewritten"):
        run(str(input_file), provider="askllm2", verbose=True)
    assert input_file.read_text() == "rewritten"


def test_askllm2_preserves_symlink_and_permissions(tmp_path: Path):
    source = tmp_path / "source.md"
    source.write_text("original")
    source.chmod(0o640)
    link = tmp_path / "link.md"
    link.symlink_to(source)
    with patch.object(AskLLM2Client, "complete", return_value="rewritten"):
        run(str(link), provider="askllm2", verbose=True)
    assert link.is_symlink()
    assert source.read_text() == "rewritten"
    assert source.stat().st_mode & 0o777 == 0o640


def test_askllm2_recursive_writes_each_file(tmp_path: Path):
    source = tmp_path / "input"
    source.mkdir()
    (source / "one.md").write_text("original")
    out = tmp_path / "output"
    with patch.object(AskLLM2Client, "complete", return_value="rewritten"):
        run(str(source), str(out), provider="askllm2", recurse="*.md", workers=1, verbose=True)
    assert (source / "one.md").read_text() == "original"
    assert (out / "one.md").read_text() == "rewritten"


def test_askllm2_explain_parses_metadata():
    client = AskLLM2Client("auto")
    with patch.object(client, "complete", return_value='{"title": "New title"}') as complete:
        result = client.explain_metadata({}, "example document", 0.3, 0.9)
    assert result == {"title": "New title"}
    assert "example document" in complete.call_args.args[0][0]["content"]


def test_askllm2_rejects_bad_subprocess_response():
    client = AskLLM2Client("auto")
    with patch("cerebrate_file.askllm2.subprocess.run") as mock:
        mock.return_value = SimpleNamespace(returncode=1, stdout="partial")
        with pytest.raises(RuntimeError, match="exit status"):
            client.complete([{"role": "user", "content": "private"}], 128, 0.2, 0.8)


@pytest.mark.parametrize("recursive", [False, True])
def test_askllm2_explain_failure_preserves_files_and_fails(tmp_path: Path, monkeypatch, recursive):
    source_dir = tmp_path / "input"
    source_dir.mkdir()
    source = source_dir / "document.md"
    source.write_text("original")
    output = tmp_path / "output.md"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "document.md").write_text("existing")
    output.write_text("existing")
    monkeypatch.setattr(
        "cerebrate_file.cli.check_metadata_completeness", lambda _: (False, ["title"])
    )
    paths = (str(source_dir), str(output_dir)) if recursive else (str(source), str(output))
    options = {"recurse": "*.md", "workers": 1} if recursive else {}
    with (
        patch.object(
            AskLLM2Client, "explain_metadata", side_effect=RuntimeError("metadata failed")
        ),
        patch.object(AskLLM2Client, "complete") as complete,
        pytest.raises(RuntimeError, match="failed"),
    ):
        run(*paths, provider="askllm2", force=True, explain=True, verbose=True, **options)
    complete.assert_not_called()
    assert source.read_text() == "original"
    assert output.read_text() == "existing"
    assert (output_dir / "document.md").read_text() == "existing"


def test_askllm2_recursive_chunk_failure_raises(tmp_path: Path):
    source = tmp_path / "input"
    source.mkdir()
    (source / "document.md").write_text("original")
    output = tmp_path / "output"
    with (
        patch.object(AskLLM2Client, "complete", side_effect=RuntimeError("request failed")),
        pytest.raises(RuntimeError, match="failed during recursive"),
    ):
        run(str(source), str(output), provider="askllm2", recurse="*.md", workers=1, verbose=True)
    assert (source / "document.md").read_text() == "original"
    assert not (output / "document.md").exists()


@pytest.mark.parametrize("recursive", [False, True])
def test_askllm2_explain_only_adds_missing_metadata(tmp_path: Path, monkeypatch, recursive):
    from cerebrate_file.file_utils import parse_frontmatter_content

    source_dir = tmp_path / "input"
    source_dir.mkdir()
    source = source_dir / "document.md"
    source.write_text("---\ntitle: Original\n---\nText")
    output = tmp_path / "output.md"
    output_dir = tmp_path / "output"
    monkeypatch.setattr(
        "cerebrate_file.cli.check_metadata_completeness", lambda _: (False, ["description"])
    )
    with (
        patch.object(
            AskLLM2Client,
            "explain_metadata",
            return_value={"title": "Overwritten", "description": "Summary", "surprise": "Injected"},
        ),
        patch.object(AskLLM2Client, "complete", return_value="Rewritten"),
    ):
        if recursive:
            run(
                str(source_dir),
                str(output_dir),
                provider="askllm2",
                recurse="*.md",
                workers=1,
                explain=True,
                verbose=True,
            )
            output = output_dir / "document.md"
        else:
            run(str(source), str(output), provider="askllm2", explain=True, verbose=True)
    metadata, _ = parse_frontmatter_content(output.read_text())
    assert metadata["title"] == "Original"
    assert metadata["description"] == "Summary"
    assert "surprise" not in metadata
