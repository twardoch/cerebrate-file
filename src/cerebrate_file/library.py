# this_file: src/cerebrate_file/library.py
"""Public functions for transforming text and files from Python."""

import os
from pathlib import Path
from typing import Any

from cerebras.cloud.sdk import Cerebras

from .askllm2 import AskLLM2Client
from .cerebrate_file import process_document
from .chunking import create_chunks
from .file_utils import ProgressiveFileWriter
from .settings import get_settings
from .tokenizer import encode_text


def process_text(
    text: str,
    prompt: str,
    *,
    provider: str = "cerebras",
    model: str | None = None,
    data_format: str = "markdown",
    chunk_size: int | None = None,
    sample_size: int | None = None,
    max_tokens_ratio: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
) -> str:
    """Transform text with chunking; raise on any failed or empty chunk.

    The default provider matches the CLI. Set provider="askllm2" to use the
    active FreeLLM chain, optionally selecting a Poe bot with model="poe:BOT".
    Remaining options default to the project's layered configuration.
    """
    if not prompt.strip():
        raise ValueError("prompt must not be empty")
    if provider not in {"cerebras", "askllm2"}:
        raise ValueError("provider must be cerebras or askllm2")
    settings = get_settings()
    chunk_size = settings.inference.chunk_size if chunk_size is None else chunk_size
    sample_size = settings.inference.sample_size if sample_size is None else sample_size
    max_tokens_ratio = (
        settings.inference.max_tokens_ratio if max_tokens_ratio is None else max_tokens_ratio
    )
    temperature = settings.inference.temperature if temperature is None else temperature
    top_p = settings.inference.top_p if top_p is None else top_p
    if chunk_size <= 0 or sample_size < 0 or max_tokens_ratio <= 0:
        raise ValueError(
            "chunk_size and max_tokens_ratio must be positive; sample_size nonnegative"
        )
    if not 0 <= temperature <= 2 or not 0 <= top_p <= 1:
        raise ValueError("temperature must be 0..2 and top_p must be 0..1")
    if not text:
        return ""
    chunks = create_chunks(text, data_format, chunk_size)
    if not chunks:
        raise ValueError("Nonempty input produced no chunks")
    client: Any
    if provider == "askllm2":
        model = model or "auto"
        client = AskLLM2Client(model)
    else:
        model = model or settings.get_default_model_name()
        key = os.environ.get("CEREBRAS_API_KEY")
        if not key:
            raise ValueError("Set CEREBRAS_API_KEY or choose provider='askllm2'")
        client = Cerebras(api_key=key)
    result, _ = process_document(
        client,
        chunks,
        prompt,
        len(encode_text(prompt)),
        model,
        temperature,
        top_p,
        max_tokens_ratio,
        sample_size,
        raise_on_error=True,
    )
    return result


def process_file(
    input_path: str | Path,
    prompt: str,
    *,
    output_path: str | Path | None = None,
    **options: Any,
) -> str:
    """Transform a UTF-8 file, optionally writing the complete result atomically.

    The source is left alone unless output_path explicitly names it. The result
    is always returned and no file is written when model processing fails.
    """
    source = Path(input_path)
    text = source.read_text(encoding="utf-8")
    result = process_text(text, prompt, **options)
    if output_path is not None:
        with ProgressiveFileWriter(output_path, input_path=source, atomic=True) as writer:
            writer.write_chunk(result)
    return result
