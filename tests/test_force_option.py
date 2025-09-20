#!/usr/bin/env python3
# this_file: tests/test_force_option.py

"""Tests for the --force option functionality.

Tests verify that files are skipped when output exists and --force is not provided,
and that files are processed when --force is provided.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from cerebrate_file.cli import run as cli_run


@pytest.fixture
def sample_input_file():
    """Create a temporary input file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("""# Test Document

This is a test document for force option testing.

## Section 1
Some content that can be processed.

## Section 2
More content for testing.
""")
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def existing_output_file():
    """Create a temporary output file that already exists."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".out.txt", delete=False) as f:
        f.write("Existing output content that should not be overwritten")
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_directory():
    """Create a temporary directory for recursive testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create input directory structure
        input_dir = Path(temp_dir) / "input"
        output_dir = Path(temp_dir) / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        # Create test files
        (input_dir / "test1.txt").write_text("Content of test1")
        (input_dir / "test2.txt").write_text("Content of test2")

        # Create existing output files
        (output_dir / "test1.txt").write_text("Existing output 1")
        (output_dir / "test2.txt").write_text("Existing output 2")

        yield {"input": input_dir, "output": output_dir}


def test_force_option_when_output_exists_single_file(sample_input_file, existing_output_file):
    """Test that --force=False skips processing when output file exists."""
    # Mock API key validation and chunking to avoid actual API calls
    with patch("cerebrate_file.config.validate_api_key", return_value=True), \
         patch("cerebrate_file.config.validate_environment"), \
         patch("cerebrate_file.chunking.create_chunks", return_value=[]):

        # Call without force - should skip processing
        cli_run(
            input_data=sample_input_file,
            output_data=existing_output_file,
            force=False,
            dry_run=False,
            verbose=True
        )

        # Output file should still contain original content
        with open(existing_output_file, "r") as f:
            content = f.read()
        assert "Existing output content" in content
        assert "Test Document" not in content


def test_force_option_when_output_exists_force_true(sample_input_file, existing_output_file):
    """Test that --force=True processes file even when output exists."""
    # Mock everything to avoid actual API calls but allow file operations
    with patch("cerebrate_file.config.validate_api_key", return_value=True), \
         patch("cerebrate_file.config.validate_environment"), \
         patch("cerebrate_file.chunking.create_chunks") as mock_chunks, \
         patch("cerebrate_file.cerebrate_file.process_document") as mock_process, \
         patch("cerebras.cloud.sdk.Cerebras"):

        # Setup mocks
        mock_chunks.return_value = []  # Empty chunks to skip processing
        mock_process.return_value = ("Processed content", type('State', (), {
            'processing_time': 1.0,
            'chunks_processed': 0,
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'last_rate_status': type('RateStatus', (), {
                'headers_parsed': False,
                'requests_remaining': None
            })()
        })())

        # Call with force=True - should process file
        cli_run(
            input_data=sample_input_file,
            output_data=existing_output_file,
            force=True,
            dry_run=False,
            verbose=True
        )

        # Since we mocked process_document to return empty chunks,
        # the file should be overwritten with empty content
        # (in real scenario, it would contain processed content)


def test_force_option_when_input_equals_output(sample_input_file):
    """Test that force option doesn't apply when input and output paths are the same."""
    # Mock to avoid actual processing
    with patch("cerebrate_file.config.validate_api_key", return_value=True), \
         patch("cerebrate_file.config.validate_environment"), \
         patch("cerebrate_file.chunking.create_chunks", return_value=[]), \
         patch("cerebras.cloud.sdk.Cerebras"):

        # When input_data == output_data, force check should not apply
        cli_run(
            input_data=sample_input_file,
            output_data=sample_input_file,  # Same as input
            force=False,
            dry_run=False,
            verbose=True
        )

        # This should not raise any errors or skip processing


def test_force_option_when_output_does_not_exist(sample_input_file):
    """Test that processing continues normally when output file doesn't exist."""
    non_existent_output = sample_input_file + ".new_output"

    # Ensure output file doesn't exist
    if os.path.exists(non_existent_output):
        os.unlink(non_existent_output)

    try:
        # Mock to avoid actual processing
        with patch("cerebrate_file.config.validate_api_key", return_value=True), \
             patch("cerebrate_file.config.validate_environment"), \
             patch("cerebrate_file.chunking.create_chunks", return_value=[]), \
             patch("cerebras.cloud.sdk.Cerebras"):

            # Should proceed normally since output doesn't exist
            cli_run(
                input_data=sample_input_file,
                output_data=non_existent_output,
                force=False,
                dry_run=False,
                verbose=True
            )

            # This should not raise errors or skip processing
    finally:
        if os.path.exists(non_existent_output):
            os.unlink(non_existent_output)


def test_force_option_recursive_mode(temp_directory):
    """Test force option in recursive processing mode."""
    input_dir = temp_directory["input"]
    output_dir = temp_directory["output"]

    # Mock to avoid actual processing
    with patch("cerebrate_file.config.validate_api_key", return_value=True), \
         patch("cerebrate_file.config.validate_environment"), \
         patch("cerebrate_file.config.validate_recursive_inputs"), \
         patch("cerebrate_file.recursive.find_files_recursive") as mock_find_files, \
         patch("cerebrate_file.recursive.process_files_parallel") as mock_process_parallel:

        # Setup mocks for recursive processing
        file_pairs = [
            (input_dir / "test1.txt", output_dir / "test1.txt"),
            (input_dir / "test2.txt", output_dir / "test2.txt"),
        ]
        mock_find_files.return_value = file_pairs

        # Mock the parallel processing result
        mock_result = type('Result', (), {
            'successful': [],
            'failed': [],
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_time': 1.0
        })()
        mock_process_parallel.return_value = mock_result

        # Test recursive processing without force
        cli_run(
            input_data=str(input_dir),
            output_data=str(output_dir),
            recurse="*.txt",
            force=False,
            dry_run=False,
            verbose=True
        )

        # Verify that recursive processing was attempted
        mock_find_files.assert_called_once()
        mock_process_parallel.assert_called_once()


def test_force_option_dry_run_mode(sample_input_file, existing_output_file):
    """Test that force option works correctly in dry-run mode."""
    # Mock to avoid actual processing
    with patch("cerebrate_file.config.validate_api_key", return_value=True), \
         patch("cerebrate_file.config.validate_environment"):

        # Test dry-run with existing output file - should not check force
        cli_run(
            input_data=sample_input_file,
            output_data=existing_output_file,
            force=False,
            dry_run=True,
            verbose=True
        )

        # In dry-run mode, force check should be bypassed
        # Original content should remain unchanged
        with open(existing_output_file, "r") as f:
            content = f.read()
        assert "Existing output content" in content


def test_force_option_parameter_validation():
    """Test that force parameter is properly validated."""
    # Test default value
    with patch("cerebrate_file.config.validate_api_key", return_value=True), \
         patch("cerebrate_file.config.validate_environment"), \
         patch("cerebrate_file.chunking.create_chunks", return_value=[]):

        # Create temporary files
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as input_f:
            input_f.write("test content")
            input_path = input_f.name

        try:
            # Test with force=True
            cli_run(
                input_data=input_path,
                force=True,
                dry_run=True,
                verbose=False
            )

            # Test with force=False (default)
            cli_run(
                input_data=input_path,
                force=False,
                dry_run=True,
                verbose=False
            )

        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)


def test_force_option_logged_messages(sample_input_file, existing_output_file, capsys):
    """Test that appropriate messages are generated for force option."""
    # Mock to avoid actual processing
    with patch("cerebrate_file.config.validate_api_key", return_value=True), \
         patch("cerebrate_file.config.validate_environment"), \
         patch("cerebrate_file.chunking.create_chunks", return_value=[]):

        # Use verbose mode to enable INFO logging level
        cli_run(
            input_data=sample_input_file,
            output_data=existing_output_file,
            force=False,
            dry_run=False,
            verbose=True  # Enable verbose to capture INFO logs
        )

        # Check that appropriate warning message was displayed
        captured = capsys.readouterr()
        assert "already exists. Use --force to overwrite" in captured.out