#!/usr/bin/env python3
# this_file: tests/test_models.py

"""Tests for cerebrate_file.models module."""

import pytest
from datetime import datetime, timedelta
from cerebrate_file.models import (
    Chunk,
    RateLimitStatus,
    ProcessingState,
    ProcessingResult,
    ChunkingConfig,
    APIConfig,
)


def test_chunk_creation():
    """Test Chunk dataclass creation and methods."""
    chunk = Chunk(text="Hello world", token_count=2)
    assert chunk.text == "Hello world"
    assert chunk.token_count == 2
    assert chunk.metadata is None
    assert len(chunk) == 2
    assert not chunk.is_empty()


def test_chunk_with_metadata():
    """Test Chunk with metadata."""
    metadata = {"source": "test", "line": 1}
    chunk = Chunk(text="Hello", token_count=1, metadata=metadata)
    assert chunk.metadata == metadata


def test_chunk_empty():
    """Test empty chunk detection."""
    empty_chunk = Chunk(text="", token_count=0)
    assert empty_chunk.is_empty()

    whitespace_chunk = Chunk(text="   \n\t  ", token_count=0)
    assert whitespace_chunk.is_empty()

    non_empty_chunk = Chunk(text="Hello", token_count=1)
    assert not non_empty_chunk.is_empty()


def test_rate_limit_status():
    """Test RateLimitStatus dataclass."""
    now = datetime.now()
    rate_limit = RateLimitStatus(
        requests_remaining=100,
        tokens_remaining=50000,
        reset_time=now + timedelta(minutes=1),
    )
    assert rate_limit.requests_remaining == 100
    assert rate_limit.tokens_remaining == 50000
    assert rate_limit.reset_time > now


def test_processing_state():
    """Test ProcessingState dataclass."""
    state = ProcessingState(
        prev_input_text="Previous input",
        prev_output_text="Previous output",
        total_input_tokens=1000,
        total_output_tokens=500,
        chunks_processed=5,
    )
    assert state.prev_input_text == "Previous input"
    assert state.prev_output_text == "Previous output"
    assert state.total_input_tokens == 1000
    assert state.total_output_tokens == 500
    assert state.chunks_processed == 5


def test_processing_result():
    """Test ProcessingResult dataclass."""
    result = ProcessingResult(
        output_text="Processed content",
        chunks_processed=1,
        total_input_tokens=100,
        total_output_tokens=50,
        processing_time=1.5,
    )
    assert result.output_text == "Processed content"
    assert result.chunks_processed == 1
    assert result.total_input_tokens == 100
    assert result.total_output_tokens == 50
    assert result.processing_time == 1.5


def test_chunking_config():
    """Test ChunkingConfig dataclass."""
    config = ChunkingConfig(chunk_size=1000, data_format="text", sample_size=200)
    assert config.chunk_size == 1000
    assert config.data_format == "text"
    assert config.sample_size == 200


def test_api_config():
    """Test APIConfig dataclass."""
    config = APIConfig(
        model="test-model", temperature=0.98, top_p=0.9, max_tokens_ratio=100
    )
    assert config.model == "test-model"
    assert config.temperature == 0.98
    assert config.top_p == 0.9
    assert config.max_tokens_ratio == 100
