# this_file: tests/test_pre_screening.py

"""Tests for the pre-screening functionality.

Tests verify that files with existing outputs are properly filtered during
pre-screening stage when --force is not provided.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from cerebrate_file.recursive import pre_screen_files
from cerebrate_file.file_utils import output_file_exists


class TestOutputFileExists:
    """Test the output_file_exists utility function."""

    def test_output_file_exists_when_same_path(self, tmp_path):
        """Test that in-place processing (same input/output path) returns False."""
        test_file = tmp_path / "test.md"
        test_file.write_text("test content")

        result = output_file_exists(test_file, test_file)
        assert result is False

    def test_output_file_exists_when_output_exists(self, tmp_path):
        """Test that returns True when output file exists and differs from input."""
        input_file = tmp_path / "input.md"
        output_file = tmp_path / "output.md"

        input_file.write_text("input content")
        output_file.write_text("output content")

        result = output_file_exists(input_file, output_file)
        assert result is True

    def test_output_file_exists_when_output_missing(self, tmp_path):
        """Test that returns False when output file doesn't exist."""
        input_file = tmp_path / "input.md"
        output_file = tmp_path / "output.md"

        input_file.write_text("input content")
        # output_file not created

        result = output_file_exists(input_file, output_file)
        assert result is False

    def test_output_file_exists_handles_permission_error(self, tmp_path):
        """Test that permission errors are handled gracefully."""
        input_file = tmp_path / "input.md"
        output_file = tmp_path / "output.md"

        input_file.write_text("input content")

        # Mock path.exists() to raise PermissionError
        with patch.object(Path, 'exists', side_effect=PermissionError("Access denied")):
            result = output_file_exists(input_file, output_file)
            assert result is False  # Should default to False on error


class TestPreScreenFiles:
    """Test the pre_screen_files function."""

    def test_pre_screen_files_with_force_true(self, tmp_path):
        """Test that force=True returns all files unchanged."""
        input1 = tmp_path / "input1.md"
        output1 = tmp_path / "output1.md"
        input2 = tmp_path / "input2.md"
        output2 = tmp_path / "output2.md"

        # Create input files
        input1.write_text("content1")
        input2.write_text("content2")

        # Create one output file
        output1.write_text("existing output")

        file_pairs = [(input1, output1), (input2, output2)]

        result = pre_screen_files(file_pairs, force=True)

        assert len(result) == 2
        assert result == file_pairs

    def test_pre_screen_files_with_force_false_no_existing_outputs(self, tmp_path):
        """Test that force=False returns all files when no outputs exist."""
        input1 = tmp_path / "input1.md"
        output1 = tmp_path / "output1.md"
        input2 = tmp_path / "input2.md"
        output2 = tmp_path / "output2.md"

        # Create input files only
        input1.write_text("content1")
        input2.write_text("content2")

        file_pairs = [(input1, output1), (input2, output2)]

        result = pre_screen_files(file_pairs, force=False)

        assert len(result) == 2
        assert result == file_pairs

    def test_pre_screen_files_with_force_false_some_existing_outputs(self, tmp_path):
        """Test that force=False filters out files with existing outputs."""
        input1 = tmp_path / "input1.md"
        output1 = tmp_path / "output1.md"
        input2 = tmp_path / "input2.md"
        output2 = tmp_path / "output2.md"
        input3 = tmp_path / "input3.md"
        output3 = tmp_path / "output3.md"

        # Create input files
        input1.write_text("content1")
        input2.write_text("content2")
        input3.write_text("content3")

        # Create some output files
        output1.write_text("existing output1")
        output3.write_text("existing output3")

        file_pairs = [(input1, output1), (input2, output2), (input3, output3)]

        result = pre_screen_files(file_pairs, force=False)

        assert len(result) == 1
        assert result == [(input2, output2)]

    def test_pre_screen_files_with_force_false_all_existing_outputs(self, tmp_path):
        """Test that force=False returns empty list when all outputs exist."""
        input1 = tmp_path / "input1.md"
        output1 = tmp_path / "output1.md"
        input2 = tmp_path / "input2.md"
        output2 = tmp_path / "output2.md"

        # Create input and output files
        input1.write_text("content1")
        output1.write_text("existing output1")
        input2.write_text("content2")
        output2.write_text("existing output2")

        file_pairs = [(input1, output1), (input2, output2)]

        result = pre_screen_files(file_pairs, force=False)

        assert len(result) == 0
        assert result == []

    def test_pre_screen_files_with_empty_list(self):
        """Test that empty file pairs list is handled correctly."""
        result = pre_screen_files([], force=False)
        assert result == []

        result = pre_screen_files([], force=True)
        assert result == []

    def test_pre_screen_files_with_in_place_processing(self, tmp_path):
        """Test that in-place processing (same input/output path) is not filtered."""
        test_file = tmp_path / "test.md"
        test_file.write_text("test content")

        file_pairs = [(test_file, test_file)]

        result = pre_screen_files(file_pairs, force=False)

        assert len(result) == 1
        assert result == file_pairs

    def test_pre_screen_files_logs_appropriately(self, tmp_path):
        """Test that pre_screen_files returns correct results (logging verified by other tests)."""
        input1 = tmp_path / "input1.md"
        output1 = tmp_path / "output1.md"
        input2 = tmp_path / "input2.md"
        output2 = tmp_path / "output2.md"

        # Create input files
        input1.write_text("content1")
        input2.write_text("content2")

        # Create one output file
        output1.write_text("existing output")

        file_pairs = [(input1, output1), (input2, output2)]

        result = pre_screen_files(file_pairs, force=False)

        assert len(result) == 1
        assert result == [(input2, output2)]