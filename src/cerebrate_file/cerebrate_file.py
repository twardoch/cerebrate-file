#!/usr/bin/env python3
# this_file: src/cerebrate_file/cerebrate_file.py

"""Main processing logic for cerebrate_file package.

This module contains the core document processing pipeline that chunks
large documents and processes them through Cerebras AI models.
"""

import json
import math
import time
from typing import Any

from loguru import logger

from .api_client import make_request_with_fallback

# from .chunking import create_chunks  # unused
# from .config import validate_environment, validate_inputs  # unused
from .constants import (
    MAX_CONTEXT_TOKENS,
    MAX_OUTPUT_TOKENS,
    MIN_COMPLETION_TOKENS,
    REASONING_COMPLETION_RATIO,
)
from .continuity import (
    build_continuity_block,
    extract_continuity_examples,
    fit_continuity_to_budget,
)
from .error_recovery import format_error_message

# from .file_utils import build_base_prompt, read_file_safely, write_output_atomically  # unused
from .models import Chunk, ChunkDiagnostics, ProcessingState, RateLimitStatus
from .tokenizer import encode_text

__all__ = [
    "calculate_completion_budget",
    "prepare_chunk_messages",
    "process_document",
]


def calculate_completion_budget(chunk_tokens: int, max_tokens_ratio: int) -> int:
    """Calculate max_completion_tokens for this chunk.

    Cerebras recently introduced verbose reasoning streams that easily
    consume thousands of completion tokens before emitting user-facing
    content. This helper therefore guarantees a generous minimum budget
    and a reasoning multiplier so each chunk can finish its thought.

    Args:
        chunk_tokens: Number of tokens in the current chunk
        max_tokens_ratio: Completion budget as percentage of chunk size

    Returns:
        Maximum completion tokens (capped at 40000)
    """
    if chunk_tokens < 0:
        raise ValueError("chunk_tokens must be non-negative")

    # Baseline requested from the user-provided ratio
    requested_tokens = (chunk_tokens * max_tokens_ratio) // 100

    # Allocate extra headroom for reasoning-heavy models (e.g., zai-glm-4.6)
    reasoning_target = math.ceil(chunk_tokens * REASONING_COMPLETION_RATIO / 100)

    # Even tiny chunks (frontmatter) need a few thousand tokens to finish reasoning
    minimum_budget = MIN_COMPLETION_TOKENS if chunk_tokens > 0 else MIN_COMPLETION_TOKENS

    effective_tokens = max(requested_tokens, reasoning_target, minimum_budget)
    max_completion_tokens = min(MAX_OUTPUT_TOKENS, effective_tokens)

    logger.debug(
        "Completion budget: chunk=%s tokens, ratio=%s%% -> requested=%s, "
        "reasoning_target=%s, floor=%s, capped=%s",
        chunk_tokens,
        max_tokens_ratio,
        requested_tokens,
        reasoning_target,
        minimum_budget,
        max_completion_tokens,
    )

    return max_completion_tokens


def prepare_chunk_messages(
    base_prompt: str,
    chunk: Chunk,
    continuity_block: str,
    base_prompt_tokens: int,
    metadata: dict[str, Any] | None = None,
) -> tuple[list[dict[str, str]], int]:
    """Prepare chat messages for API call with token validation.

    Args:
        base_prompt: System prompt text
        chunk: Current chunk to process
        continuity_block: Continuity context (may be empty)
        base_prompt_tokens: Token count for base prompt
        metadata: Optional metadata to include as context

    Returns:
        Tuple of (messages list, total_input_tokens)
    """
    # Prepare metadata context if provided
    metadata_context = ""
    if metadata:
        # Convert any non-serializable objects to strings
        serializable_metadata = {}
        for key, value in metadata.items():
            try:
                json.dumps(value)
                serializable_metadata[key] = value
            except TypeError:
                serializable_metadata[key] = str(value)

        metadata_json = json.dumps(serializable_metadata, separators=(",", ":"))
        metadata_context = (
            f"Our current input text chunk is part of the document {metadata_json}\n\n"
        )

    # Combine user content: metadata_context + continuity + chunk
    user_content_parts = []
    if metadata_context:
        user_content_parts.append(metadata_context)
    if continuity_block:
        user_content_parts.append(continuity_block)
    user_content_parts.append(chunk.text)

    user_content = "".join(user_content_parts)

    # Calculate total input tokens
    user_tokens = len(encode_text(user_content))
    total_input_tokens = base_prompt_tokens + user_tokens

    # Validate within actual model context window (131K tokens)
    if total_input_tokens > MAX_CONTEXT_TOKENS:
        logger.error(
            f"Total input tokens ({total_input_tokens}) exceeds context window limit ({MAX_CONTEXT_TOKENS})"
        )
        raise ValueError(
            f"Input too large: {total_input_tokens} tokens > {MAX_CONTEXT_TOKENS} limit"
        )

    # Prepare messages
    messages = [
        {"role": "system", "content": base_prompt},
        {"role": "user", "content": user_content},
    ]

    logger.debug(
        f"Messages prepared: {base_prompt_tokens} system + {user_tokens} user = "
        f"{total_input_tokens} total input tokens"
    )

    return messages, total_input_tokens


def process_document(
    client,
    chunks: list[Chunk],
    base_prompt: str,
    base_prompt_tokens: int,
    model: str,
    temp: float,
    top_p: float,
    max_tokens_ratio: int,
    sample_size: int,
    metadata: dict[str, Any] | None = None,
    verbose: bool = False,
    progress_callback: object | None = None,
) -> tuple[str, ProcessingState]:
    """Process all chunks through the Cerebras API.

    Args:
        client: Initialized Cerebras client
        chunks: List of chunks to process
        base_prompt: System prompt text
        base_prompt_tokens: Token count for base prompt
        model: Model name
        temp: Temperature parameter
        top_p: Top-p parameter
        max_tokens_ratio: Completion budget ratio
        sample_size: Continuity sample size
        metadata: Optional metadata
        verbose: Enable verbose output
        progress_callback: Optional callback function for progress updates.
                          Called with (chunks_completed, remaining_calls)

    Returns:
        Tuple of (final_output, processing_state)
    """
    from .api_client import calculate_backoff_delay

    logger.info(f"Starting processing of {len(chunks)} chunks")
    start_time = time.time()

    state = ProcessingState()
    results = []
    last_rate_status = RateLimitStatus()

    for i, chunk in enumerate(chunks):
        # Show progress differently based on verbose mode
        if verbose:
            print(f"[{i + 1}/{len(chunks)}] Processing chunk ({chunk.token_count} tokens)...")

        logger.info(f"Processing chunk {i + 1}/{len(chunks)} ({chunk.token_count} tokens)")

        try:
            # Build continuity block if this isn't the first chunk
            continuity_block = ""
            if i > 0 and sample_size > 0 and state.prev_input_tokens and state.prev_output_tokens:
                if verbose:
                    print(
                        f"  → Building continuity from previous {len(state.prev_input_tokens)} input + {len(state.prev_output_tokens)} output tokens"
                    )

                input_example = extract_continuity_examples(
                    state.prev_input_text, state.prev_input_tokens, sample_size
                )
                output_example = extract_continuity_examples(
                    state.prev_output_text, state.prev_output_tokens, sample_size
                )

                if input_example and output_example:
                    continuity_block = build_continuity_block(input_example, output_example)
                    # Fit within token budget
                    base_tokens = base_prompt_tokens + chunk.token_count
                    continuity_block = fit_continuity_to_budget(continuity_block, base_tokens)
                    continuity_tokens = (
                        len(encode_text(continuity_block)) if continuity_block else 0
                    )

                    if verbose and continuity_block:
                        print(f"  → Continuity added: {continuity_tokens} tokens")
                    elif verbose:
                        print("  → Continuity dropped (budget exceeded)")

            # Prepare messages
            messages, total_input_tokens = prepare_chunk_messages(
                base_prompt,
                chunk,
                continuity_block,
                base_prompt_tokens,
                metadata,
            )

            # Calculate completion budget
            max_completion_tokens = calculate_completion_budget(chunk.token_count, max_tokens_ratio)

            if verbose:
                print(
                    f"  → Request: {total_input_tokens} input tokens → max {max_completion_tokens} completion tokens"
                )

            # Apply rate limiting delay if needed
            if i > 0:  # Don't delay before first chunk
                next_chunk_tokens = chunks[i].token_count if i < len(chunks) - 1 else 0
                delay = calculate_backoff_delay(last_rate_status, next_chunk_tokens)
                if delay > 0:
                    if verbose:
                        print(f"  → Rate limit delay: {delay:.1f}s")
                    logger.info(f"Rate limit delay: {delay:.1f}s")
                    time.sleep(delay)

            # Make API request
            logger.debug(
                f"Making Cerebras request: {total_input_tokens} input tokens, "
                f"{max_completion_tokens} max completion tokens"
            )

            if verbose:
                print("  → Calling Cerebras API...")

            response_text, rate_status, model_used = make_request_with_fallback(
                client, messages, model, max_completion_tokens, temp, top_p, verbose
            )
            if model_used != model:
                logger.info(f"Response from fallback model: {model_used}")

            # Update state for next iteration
            state.prev_input_text = chunk.text
            state.prev_input_tokens = encode_text(chunk.text)
            state.prev_output_text = response_text
            state.prev_output_tokens = encode_text(response_text)
            response_tokens = len(state.prev_output_tokens)

            state.total_input_tokens += total_input_tokens
            state.total_output_tokens += response_tokens
            state.chunks_processed += 1

            results.append(response_text)
            last_rate_status = rate_status

            diagnostic = ChunkDiagnostics(
                chunk_index=i + 1,
                chunk_tokens=chunk.token_count,
                total_input_tokens=total_input_tokens,
                max_completion_tokens=max_completion_tokens,
                response_tokens=response_tokens,
                response_chars=len(response_text),
                model=model_used,
                temperature=temp,
                top_p=top_p,
                rate_requests_remaining=rate_status.requests_remaining
                if rate_status.headers_parsed
                else None,
                rate_tokens_remaining=rate_status.tokens_remaining
                if rate_status.headers_parsed
                else None,
                rate_headers_parsed=rate_status.headers_parsed,
            )
            state.add_chunk_diagnostic(diagnostic)

            if response_tokens == 0:
                warning_payload = diagnostic.to_log_dict()
                logger.warning(
                    f"Chunk {i + 1} returned zero tokens. Request diagnostics: {warning_payload}"
                )
                if verbose:
                    print("  ⚠️  Chunk produced zero tokens. Inspect logs for diagnostics.")

            # Show completion progress
            if verbose:
                print(f"  ✓ Chunk {i + 1} complete: {response_tokens} tokens generated")
                if rate_status.headers_parsed:
                    print(
                        f"  → Rate status: {rate_status.requests_remaining} requests, {rate_status.tokens_remaining} tokens remaining"
                    )

            # Call progress callback if provided
            if progress_callback:
                remaining_calls = (
                    rate_status.requests_remaining if rate_status.headers_parsed else 0
                )
                progress_callback(i + 1, remaining_calls)

            logger.info(
                f"Chunk {i + 1} complete: {len(response_text)} chars, "
                f"{response_tokens} tokens generated"
            )

        except Exception as e:
            error_msg = format_error_message(e)
            if verbose:
                print(f"  ✗ Chunk {i + 1} failed: {error_msg}")

            # Call progress callback even for failed chunks
            if progress_callback:
                remaining_calls = (
                    last_rate_status.requests_remaining if last_rate_status.headers_parsed else 0
                )
                progress_callback(i + 1, remaining_calls)

            logger.error(f"Failed to process chunk {i + 1}: {error_msg}")
            # For now, continue with remaining chunks rather than failing entirely
            results.append(f"[ERROR: Chunk {i + 1} failed - {e!s}]")

    # Combine all results
    final_output = "".join(results)
    processing_time = time.time() - start_time

    # Update processing time in state
    state.processing_time = processing_time
    state.last_rate_status = last_rate_status

    return final_output, state
