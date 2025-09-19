#!/usr/bin/env python3
# this_file: tests/test_recursive_integration.py

"""Integration tests for recursive file processing functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from cerebrate_file.recursive import (
    find_files_recursive,
    replicate_directory_structure,
    process_files_parallel,
    ProcessingResult,
)
from cerebrate_file.models import ProcessingState


class TestRecursiveIntegration:
    """Integration tests for recursive processing functionality."""

    @pytest.fixture
    def temp_dir_structure(self):
        """Create a temporary directory structure for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test directory structure
            (temp_path / "subdir1").mkdir()
            (temp_path / "subdir2").mkdir()
            (temp_path / "nested" / "deep").mkdir(parents=True)

            # Create test files
            test_files = [
                "test1.md",
                "script.py",
                "config.json",
                "subdir1/test2.md",
                "subdir1/app.js",
                "subdir2/test3.md",
                "subdir2/data.csv",
                "nested/readme.txt",
                "nested/deep/config.yaml",
            ]

            for file_path in test_files:
                full_path = temp_path / file_path
                full_path.write_text(f"Content of {file_path}")

            yield temp_path

    def test_simple_markdown_processing(self, temp_dir_structure):
        """Test basic recursive processing of markdown files."""
        temp_dir = temp_dir_structure
        output_dir = temp_dir / "output"

        # Find markdown files
        file_pairs = find_files_recursive(temp_dir, "**/*.md", output_dir)

        # Should find 3 markdown files
        assert len(file_pairs) == 3

        # Check file mappings
        input_files = [str(pair[0].relative_to(temp_dir)) for pair in file_pairs]
        expected_files = ["test1.md", "subdir1/test2.md", "subdir2/test3.md"]

        for expected in expected_files:
            assert expected in input_files

        # Check output paths
        for input_path, output_path in file_pairs:
            relative_path = input_path.relative_to(temp_dir)
            expected_output = output_dir / relative_path
            assert output_path == expected_output

    def test_complex_glob_patterns(self, temp_dir_structure):
        """Test brace expansion and complex patterns."""
        temp_dir = temp_dir_structure

        # Test brace pattern
        file_pairs = find_files_recursive(temp_dir, "**/*.{md,py,js}")

        # Should find: 3 md + 1 py + 1 js = 5 files
        assert len(file_pairs) == 5

        extensions = [pair[0].suffix for pair in file_pairs]
        assert ".md" in extensions
        assert ".py" in extensions
        assert ".js" in extensions

    def test_directory_structure_replication(self, temp_dir_structure):
        """Test directory structure replication."""
        temp_dir = temp_dir_structure
        output_dir = temp_dir / "output"

        # Find all files with output directory specified
        file_pairs = find_files_recursive(temp_dir, "**/*", output_dir)

        # Replicate directory structure
        replicate_directory_structure(file_pairs)

        # Check that output directories were created
        expected_dirs = [
            output_dir,
            output_dir / "subdir1",
            output_dir / "subdir2",
            output_dir / "nested",
            output_dir / "nested" / "deep",
        ]

        for expected_dir in expected_dirs:
            assert expected_dir.exists()
            assert expected_dir.is_dir()

    def test_pattern_edge_cases(self, temp_dir_structure):
        """Test edge cases in pattern matching."""
        temp_dir = temp_dir_structure

        # Test pattern that matches no files
        file_pairs = find_files_recursive(temp_dir, "**/*.nonexistent")
        assert len(file_pairs) == 0

        # Test very specific pattern
        file_pairs = find_files_recursive(temp_dir, "subdir1/*.js")
        assert len(file_pairs) == 1
        assert file_pairs[0][0].name == "app.js"

        # Test deeply nested pattern
        file_pairs = find_files_recursive(temp_dir, "nested/**/*.yaml")
        assert len(file_pairs) == 1
        assert file_pairs[0][0].name == "config.yaml"

    def test_in_place_processing(self, temp_dir_structure):
        """Test in-place processing (no output directory)."""
        temp_dir = temp_dir_structure

        # Find files for in-place processing (root level only)
        file_pairs = find_files_recursive(temp_dir, "*.md")

        # Should find 1 file at root level (test1.md)
        assert len(file_pairs) == 1

        # Input and output should be the same path
        input_path, output_path = file_pairs[0]
        assert input_path == output_path
        assert input_path.name == "test1.md"

    def test_parallel_processing_mock(self, temp_dir_structure):
        """Test parallel processing with mocked processing function."""
        temp_dir = temp_dir_structure

        # Find some files to process
        file_pairs = find_files_recursive(temp_dir, "**/*.md")

        # Mock processing function
        def mock_processing_func(input_path: Path, output_path: Path) -> ProcessingState:
            state = ProcessingState()
            state.total_input_tokens = 100
            state.total_output_tokens = 150
            state.processing_time = 1.0
            return state

        # Process files
        result = process_files_parallel(file_pairs, mock_processing_func, workers=2)

        # Check results
        assert len(result.successful) == 3
        assert len(result.failed) == 0
        assert result.total_input_tokens == 300  # 3 files * 100 tokens
        assert result.total_output_tokens == 450  # 3 files * 150 tokens
        assert result.total_time == 3.0  # 3 files * 1.0 seconds

    def test_parallel_processing_with_failures(self, temp_dir_structure):
        """Test parallel processing with some failures."""
        temp_dir = temp_dir_structure

        # Find files to process
        file_pairs = find_files_recursive(temp_dir, "**/*.{md,py}")

        # Mock processing function that fails on .py files
        def mock_processing_func(input_path: Path, output_path: Path) -> ProcessingState:
            if input_path.suffix == ".py":
                raise ValueError("Simulated processing error")

            state = ProcessingState()
            state.total_input_tokens = 100
            state.total_output_tokens = 150
            state.processing_time = 1.0
            return state

        # Process files
        result = process_files_parallel(file_pairs, mock_processing_func, workers=2)

        # Check results - should have 3 successful (.md files) and 1 failed (.py file)
        assert len(result.successful) == 3
        assert len(result.failed) == 1
        assert result.total_input_tokens == 300  # Only successful files counted
        assert result.total_output_tokens == 450

        # Check that the failed file is the Python file
        failed_file, error = result.failed[0]
        assert failed_file.suffix == ".py"
        assert "Simulated processing error" in error

    def test_empty_directory_handling(self):
        """Test handling of empty directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create empty subdirectories
            (temp_path / "empty1").mkdir()
            (temp_path / "empty2").mkdir()

            # Try to find files
            file_pairs = find_files_recursive(temp_path, "**/*.md")
            assert len(file_pairs) == 0

    def test_special_characters_in_filenames(self):
        """Test handling of files with special characters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with special characters
            special_files = [
                "file with spaces.md",
                "file-with-dashes.md",
                "file_with_underscores.md",
                "file.with.dots.md",
            ]

            for filename in special_files:
                (temp_path / filename).write_text(f"Content of {filename}")

            # Find files
            file_pairs = find_files_recursive(temp_path, "*.md")
            assert len(file_pairs) == 4

            # Check all files were found
            found_names = [pair[0].name for pair in file_pairs]
            for expected_name in special_files:
                assert expected_name in found_names

    def test_error_handling_invalid_directory(self):
        """Test error handling for invalid directories."""
        # Test non-existent directory
        with pytest.raises(ValueError, match="Input directory does not exist"):
            find_files_recursive(Path("/nonexistent/directory"), "*.md")

        # Test file instead of directory
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(ValueError, match="Input path is not a directory"):
                find_files_recursive(Path(temp_file.name), "*.md")

    def test_progress_callback_integration(self, temp_dir_structure):
        """Test progress callback integration."""
        temp_dir = temp_dir_structure

        # Find files to process
        file_pairs = find_files_recursive(temp_dir, "**/*.md")

        # Track progress callbacks
        progress_calls = []

        def progress_callback(file_path: str, completed: int):
            progress_calls.append((file_path, completed))

        # Mock processing function
        def mock_processing_func(input_path: Path, output_path: Path) -> ProcessingState:
            return ProcessingState()

        # Process files with progress callback
        result = process_files_parallel(
            file_pairs, mock_processing_func, workers=2, progress_callback=progress_callback
        )

        # Check that progress callbacks were made
        assert len(progress_calls) == 3  # One for each file
        assert all(completed == 1 for _, completed in progress_calls)

    def test_worker_count_variation(self, temp_dir_structure):
        """Test processing with different worker counts."""
        temp_dir = temp_dir_structure

        # Find files to process
        file_pairs = find_files_recursive(temp_dir, "**/*.md")

        # Mock processing function
        def mock_processing_func(input_path: Path, output_path: Path) -> ProcessingState:
            return ProcessingState()

        # Test with different worker counts
        for workers in [1, 2, 4]:
            result = process_files_parallel(file_pairs, mock_processing_func, workers=workers)
            assert len(result.successful) == 3
            assert len(result.failed) == 0

    def test_large_file_set_simulation(self):
        """Test processing a large number of files (simulated)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create many files
            for i in range(20):
                (temp_path / f"file_{i:03d}.md").write_text(f"Content {i}")

            # Find all files
            file_pairs = find_files_recursive(temp_path, "*.md")
            assert len(file_pairs) == 20

            # Mock processing function
            def mock_processing_func(input_path: Path, output_path: Path) -> ProcessingState:
                state = ProcessingState()
                state.total_input_tokens = 10
                state.total_output_tokens = 15
                state.processing_time = 0.1
                return state

            # Process with multiple workers
            result = process_files_parallel(file_pairs, mock_processing_func, workers=4)

            # Check results
            assert len(result.successful) == 20
            assert len(result.failed) == 0
            assert result.total_input_tokens == 200  # 20 * 10
            assert result.total_output_tokens == 300  # 20 * 15
            assert abs(result.total_time - 2.0) < 0.01  # 20 * 0.1 (allow for floating point precision)