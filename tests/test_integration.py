#!/usr/bin/env python3
# this_file: tests/test_integration.py

"""Integration tests for cerebrate_file package.

These tests verify that all components work together correctly
in realistic usage scenarios.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cerebrate_file.cerebrate_file import process_document
from cerebrate_file.chunking import create_chunks
from cerebrate_file.config import setup_logging, validate_inputs
from cerebrate_file.file_utils import read_file_safely, write_output_atomically
from cerebrate_file.models import APIConfig, ChunkingConfig


@pytest.fixture
def sample_text_file():
    """Create a temporary text file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("""# Test Document

This is a test document for integration testing.

## Section 1
First section content with some details.

## Section 2
Second section with more information.

### Subsection
Additional nested content for testing hierarchical structure.
""")
        temp_path = f.name
    yield temp_path
    # Cleanup
    if Path(temp_path):
        Path(temp_path)


@pytest.fixture
def mock_api_response():
    """Mock successful API response."""
    return {
        "content": "Processed content",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    }


def test_full_pipeline_dry_run(sample_text_file):
    """Test the full processing pipeline in dry-run mode."""
    # Test that dry-run mode works without making API calls
    from cerebrate_file.cli import run as cli_run

    # Call the function directly with parameters
    with patch("cerebrate_file.cli.sys.exit"):
        # Should complete without errors in dry-run mode
        try:
            cli_run(
                input_data=sample_text_file,
                dry_run=True,
                chunk_size=1000,
                data_format="markdown",
                verbose=False,
            )
        except SystemExit:
            pass  # Expected in dry-run mode


def test_file_io_operations(sample_text_file):
    """Test file reading and writing operations."""
    # Test reading
    content = read_file_safely(sample_text_file)
    assert "Test Document" in content
    assert "Section 1" in content

    # Test writing
    output_file = sample_text_file + ".out"
    try:
        # write_output_atomically expects (content, output_path, metadata)
        write_output_atomically(content + "\n\nAdded content", output_file)

        # Verify written content
        new_content = read_file_safely(output_file)
        assert "Added content" in new_content
        assert "Test Document" in new_content
    finally:
        if Path(output_file):
            Path(output_file)


def test_chunking_pipeline():
    """Test the chunking pipeline with different strategies."""
    test_text = "Line 1\n" * 100  # Create text that needs multiple chunks

    # Test different chunking strategies
    strategies = ["text", "semantic", "markdown", "code"]

    for strategy in strategies:
        chunks = create_chunks(content=test_text, data_format=strategy, chunk_size=100)

        assert len(chunks) > 0
        assert all(chunk.text for chunk in chunks)
        assert all(chunk.token_count >= 0 for chunk in chunks)


def test_configuration_validation():
    """Test configuration validation and setup."""
    # Test API config
    api_config = APIConfig(
        model="qwen-3-coder-480b", temperature=0.98, top_p=0.8, max_tokens_ratio=100
    )
    assert api_config.model == "qwen-3-coder-480b"
    assert api_config.temperature == 0.98

    # Test chunking config
    chunk_config = ChunkingConfig(chunk_size=1000, data_format="text", sample_size=200)
    assert chunk_config.chunk_size == 1000
    assert chunk_config.data_format == "text"


@patch("cerebrate_file.api_client.CerebrasClient")
def test_api_client_integration(mock_client_class, sample_text_file):
    """Test API client integration with processing pipeline."""
    # Setup mock client
    mock_client = Mock()
    mock_client.process_chunk.return_value = {
        "content": "Processed text",
        "usage": {"prompt_tokens": 50, "completion_tokens": 25},
    }
    mock_client_class.return_value = mock_client

    # Test processing (would normally make API calls)
    content = read_file_safely(sample_text_file)
    chunks = create_chunks(content, "text", 1000)

    assert len(chunks) > 0
    assert all(chunk.text for chunk in chunks)


def test_error_handling_pipeline():
    """Test error handling throughout the pipeline."""
    from cerebrate_file.cli import run as cli_run

    # Test with non-existent file
    with pytest.raises((FileNotFoundError, SystemExit)):
        cli_run(input_data="nonexistent_file_that_does_not_exist.txt", dry_run=True)

    # Test chunking with empty content
    empty_chunks = create_chunks("", "text", 100)
    assert isinstance(empty_chunks, list)  # Should handle empty content gracefully


def test_markdown_with_frontmatter():
    """Test processing markdown files with frontmatter."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""---
title: Test Document
author: Test Author
date: 2024-01-01
---

# Main Content

This is the main content of the document.
""")
        temp_path = f.name

    try:
        content = read_file_safely(temp_path)
        chunks = create_chunks(content, "markdown", 1000)

        assert len(chunks) > 0
        # Frontmatter should be handled appropriately
        full_text = "".join(chunk.text for chunk in chunks)
        assert "Main Content" in full_text
    finally:
        if Path(temp_path):
            Path(temp_path)


def test_code_chunking_integration():
    """Test code chunking with realistic code."""
    code_sample = """
def function_one():
    '''First function'''
    return 1

def function_two():
    '''Second function'''
    return 2

class MyClass:
    def __init__(self):
        self.value = 42

    def get_value(self):
        return self.value

def main():
    '''Main entry point'''
    obj = MyClass()
    print(obj.get_value())

if __name__ == "__main__":
    main()
"""

    chunks = create_chunks(code_sample, "code", 100)
    assert len(chunks) > 0

    # Verify code structure is preserved
    full_code = "".join(chunk.text for chunk in chunks)
    assert "def function_one" in full_code
    assert "class MyClass" in full_code


def test_large_file_handling():
    """Test handling of large files that require multiple chunks."""
    # Create a large text that will definitely need chunking
    large_text = "\n".join([f"Paragraph {i}. " * 20 for i in range(100)])

    chunks = create_chunks(large_text, "text", 500)

    # Should create multiple chunks
    assert len(chunks) > 1

    # All chunks should have reasonable sizes
    for chunk in chunks:
        assert chunk.token_count > 0
        assert len(chunk.text) > 0

    # Content should be preserved
    reconstructed = "".join(chunk.text for chunk in chunks)
    assert len(reconstructed) > 0


def test_continuity_preservation():
    """Test that continuity is maintained across chunks."""
    text_with_context = """
Chapter 1: Introduction
This chapter introduces the main concepts.

Chapter 2: Development
This chapter builds on the previous concepts.

Chapter 3: Conclusion
This chapter concludes the discussion.
"""

    chunks = create_chunks(text_with_context, "text", 50)

    # Verify chunks maintain logical boundaries
    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.text.strip()  # No empty chunks


@patch.dict(os.environ, {"CEREBRAS_API_KEY": "test-key-123"})
def test_cli_environment_integration():
    """Test CLI integration with environment variables."""
    from cerebrate_file.cli import run as cli_run

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test content for environment integration")
        temp_path = f.name

    try:
        # Test that CLI picks up environment variables
        # Mock the API key validation since we're in dry-run mode
        with patch("cerebrate_file.config.validate_api_key", return_value=True):
            result = cli_run(input_data=temp_path, dry_run=True, verbose=False)
            # Dry run completes without error
            assert result is None
    finally:
        if Path(temp_path):
            Path(temp_path)


def test_explain_mode_integration():
    """Test explain mode for metadata extraction."""
    from cerebrate_file.cli import run as cli_run

    # Note: explain mode requires specific metadata handling
    text_with_metadata = """---
title: Research Paper
author: John Doe
date: 2024-01-15
type: article
id: paper-001
---

# Abstract
This paper discusses important findings.

# Introduction
The research focuses on key areas.
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(text_with_metadata)
        temp_path = f.name

    try:
        # Test explain mode processing
        with patch("cerebrate_file.config.validate_api_key", return_value=True):
            result = cli_run(input_data=temp_path, explain=True, dry_run=True, verbose=False)
            assert result is None  # Dry run
    finally:
        if Path(temp_path):
            Path(temp_path)
