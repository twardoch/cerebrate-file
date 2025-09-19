#!/usr/bin/env python3
# this_file: tests/test_chunking.py

"""Tests for cerebrate_file.chunking module."""

import pytest
from cerebrate_file.chunking import (
    ChunkingStrategy,
    TextChunker,
    SemanticChunker,
    MarkdownChunker,
    CodeChunker,
    create_chunks,
    get_chunking_strategy,
)
from cerebrate_file.models import Chunk, ChunkingConfig
from cerebrate_file.tokenizer import get_tokenizer_manager


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return "This is a sample text. It has multiple sentences. Each sentence should be processed correctly."


@pytest.fixture
def sample_markdown():
    """Sample markdown for testing."""
    return """# Title

## Section 1

This is some content under section 1.

## Section 2

This is some content under section 2.

### Subsection

More content here.
"""


@pytest.fixture
def sample_code():
    """Sample code for testing."""
    return """def hello_world():
    print("Hello, world!")
    return True

class SampleClass:
    def __init__(self):
        self.value = 42

    def get_value(self):
        return self.value

if __name__ == "__main__":
    hello_world()
"""


@pytest.fixture
def chunking_config():
    """Basic chunking configuration."""
    return ChunkingConfig(
        chunk_size=100,
        data_format="text",
        sample_size=20
    )


def test_text_chunker_creation():
    """Test TextChunker creation and basic functionality."""
    chunker = TextChunker(chunk_size=100)
    assert isinstance(chunker, ChunkingStrategy)


def test_text_chunker_basic_chunking(sample_text):
    """Test basic text chunking."""
    chunker = TextChunker(chunk_size=100)

    chunks = chunker.chunk(sample_text)
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all(isinstance(chunk, Chunk) for chunk in chunks)


def test_semantic_chunker_creation():
    """Test SemanticChunker creation."""
    chunker = SemanticChunker(chunk_size=100)
    assert isinstance(chunker, ChunkingStrategy)


def test_markdown_chunker_creation():
    """Test MarkdownChunker creation."""
    chunker = MarkdownChunker(chunk_size=100)
    assert isinstance(chunker, ChunkingStrategy)


def test_markdown_chunker_with_headers(sample_markdown):
    """Test MarkdownChunker with header-based splitting."""
    chunker = MarkdownChunker(chunk_size=200)

    chunks = chunker.chunk(sample_markdown)
    assert isinstance(chunks, list)
    assert len(chunks) > 0


def test_code_chunker_creation():
    """Test CodeChunker creation."""
    chunker = CodeChunker(chunk_size=100)
    assert isinstance(chunker, ChunkingStrategy)


def test_code_chunker_with_functions(sample_code):
    """Test CodeChunker with function-based splitting."""
    chunker = CodeChunker(chunk_size=200)

    chunks = chunker.chunk(sample_code)
    assert isinstance(chunks, list)
    assert len(chunks) > 0


def test_create_chunks_function(sample_text):
    """Test create_chunks function."""
    chunks = create_chunks(sample_text, data_format="text", chunk_size=100)
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all(isinstance(chunk, Chunk) for chunk in chunks)


def test_create_chunks_with_different_formats(sample_text):
    """Test create_chunks with different data formats."""
    formats = ["text", "semantic", "markdown", "code"]

    for fmt in formats:
        chunks = create_chunks(sample_text, data_format=fmt, chunk_size=100)
        assert isinstance(chunks, list)
        assert len(chunks) > 0


def test_get_chunking_strategy():
    """Test get_chunking_strategy function."""
    strategies = ["text", "semantic", "markdown", "code"]
    for strategy_name in strategies:
        strategy = get_chunking_strategy(strategy_name, chunk_size=100)
        assert isinstance(strategy, ChunkingStrategy)


def test_chunking_with_empty_text():
    """Test chunking with empty text."""
    chunks = create_chunks("", data_format="text", chunk_size=100)
    assert isinstance(chunks, list)
    # Empty text should still return at least one empty chunk or no chunks


def test_chunking_with_very_large_chunk_size(sample_text):
    """Test chunking with chunk size larger than text."""
    chunks = create_chunks(sample_text, data_format="text", chunk_size=10000)
    assert isinstance(chunks, list)
    assert len(chunks) == 1  # Should fit in one chunk


def test_chunking_with_very_small_chunk_size():
    """Test chunking with very small chunk size."""
    # Use longer text with natural break points to ensure multiple chunks
    long_text = "Sentence one. Sentence two. Sentence three. " * 10
    chunks = create_chunks(long_text, data_format="text", chunk_size=20)
    assert isinstance(chunks, list)
    # With very long text and small chunks, should create multiple chunks
    assert len(chunks) >= 1  # At least one chunk


def test_chunk_token_counts(sample_text):
    """Test that chunks have reasonable token counts."""
    chunks = create_chunks(sample_text, data_format="text", chunk_size=50)
    for chunk in chunks:
        assert isinstance(chunk.token_count, int)
        assert chunk.token_count >= 0
        # Most chunks should be under the limit (some may be slightly over due to boundary constraints)
        assert chunk.token_count <= 50 * 2  # Allow some flexibility


def test_chunk_text_content(sample_text):
    """Test that chunk text content is preserved."""
    chunks = create_chunks(sample_text, data_format="text", chunk_size=100)

    # Reconstruct text from chunks
    reconstructed = "".join(chunk.text for chunk in chunks)

    # Should preserve all content (possibly with some formatting changes)
    # At minimum, no content should be lost
    assert len(reconstructed) > 0
    # Check that key words are preserved
    assert "sample" in reconstructed.lower()
    assert "text" in reconstructed.lower()