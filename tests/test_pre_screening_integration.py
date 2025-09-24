# this_file: tests/test_pre_screening_integration.py

"""Integration tests for pre-screening functionality in CLI.

Tests verify that pre-screening works correctly when integrated with
the recursive processing CLI interface.
"""

from unittest.mock import MagicMock, patch

import pytest

from cerebrate_file.cli import run


class TestPreScreeningIntegration:
    """Test pre-screening integration in CLI recursive mode."""

    def test_recursive_pre_screening_with_existing_outputs(self, tmp_path, capsys):
        """Test that recursive mode properly pre-screens files with existing outputs."""
        # Create input directory structure
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create input files
        (input_dir / "file1.md").write_text("content 1")
        (input_dir / "file2.md").write_text("content 2")
        (input_dir / "file3.md").write_text("content 3")

        # Create some existing output files
        (output_dir / "file1.md").write_text("existing output 1")
        (output_dir / "file3.md").write_text("existing output 3")

        # Mock the environment and processing to avoid actual API calls
        with patch.dict("os.environ", {"CEREBRAS_API_KEY": "csk-test-key-12345678"}):
            with patch("cerebrate_file.config.validate_environment"):
                with patch("cerebrate_file.recursive.process_files_parallel") as mock_process:
                    # Configure mock to return empty result
                    mock_result = MagicMock()
                    mock_result.successful = []
                    mock_result.failed = []
                    mock_result.total_input_tokens = 0
                    mock_result.total_output_tokens = 0
                    mock_result.total_time = 0.0
                    mock_process.return_value = mock_result

                    # Run with recursive mode, no force
                    run(
                        input_data=str(input_dir),
                        output_data=str(output_dir),
                        recurse="*.md",
                        force=False,
                        dry_run=False,
                        verbose=True,
                    )

                    # Check that only file2.md was scheduled for processing
                    mock_process.assert_called_once()
                    call_args = mock_process.call_args[0]
                    file_pairs = call_args[0]  # First argument is file_pairs

                    assert len(file_pairs) == 1
                    input_file, output_file = file_pairs[0]
                    assert input_file.name == "file2.md"
                    assert output_file.name == "file2.md"

        # Check console output
        captured = capsys.readouterr()
        assert (
            "Found 3 candidates, 1 will be processed (2 skipped - use --force to include)"
            in captured.out
        )

    def test_recursive_pre_screening_with_force_true(self, tmp_path, capsys):
        """Test that force=True bypasses pre-screening in recursive mode."""
        # Create input directory structure
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create input files
        (input_dir / "file1.md").write_text("content 1")
        (input_dir / "file2.md").write_text("content 2")

        # Create existing output files
        (output_dir / "file1.md").write_text("existing output 1")
        (output_dir / "file2.md").write_text("existing output 2")

        # Mock the environment and processing to avoid actual API calls
        with patch.dict("os.environ", {"CEREBRAS_API_KEY": "csk-test-key-12345678"}):
            with patch("cerebrate_file.config.validate_environment"):
                with patch("cerebrate_file.recursive.process_files_parallel") as mock_process:
                    # Configure mock to return empty result
                    mock_result = MagicMock()
                    mock_result.successful = []
                    mock_result.failed = []
                    mock_result.total_input_tokens = 0
                    mock_result.total_output_tokens = 0
                    mock_result.total_time = 0.0
                    mock_process.return_value = mock_result

                    # Run with recursive mode, force=True
                    run(
                        input_data=str(input_dir),
                        output_data=str(output_dir),
                        recurse="*.md",
                        force=True,
                        dry_run=False,
                        verbose=True,
                    )

                    # Check that all files were scheduled for processing
                    mock_process.assert_called_once()
                    call_args = mock_process.call_args[0]
                    file_pairs = call_args[0]  # First argument is file_pairs

                    assert len(file_pairs) == 2

        # Check console output
        captured = capsys.readouterr()
        assert "Found 2 files to process" in captured.out

    def test_recursive_pre_screening_all_files_filtered(self, tmp_path, capsys):
        """Test behavior when all files are filtered out by pre-screening."""
        # Create input directory structure
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create input files
        (input_dir / "file1.md").write_text("content 1")
        (input_dir / "file2.md").write_text("content 2")

        # Create all output files (so all get filtered)
        (output_dir / "file1.md").write_text("existing output 1")
        (output_dir / "file2.md").write_text("existing output 2")

        # Mock the environment to avoid validation
        with patch.dict("os.environ", {"CEREBRAS_API_KEY": "csk-test-key-12345678"}):
            with patch("cerebrate_file.config.validate_environment"):
                # Run with recursive mode, no force
                run(
                    input_data=str(input_dir),
                    output_data=str(output_dir),
                    recurse="*.md",
                    force=False,
                    dry_run=False,
                    verbose=True,
                )

        # Check console output
        captured = capsys.readouterr()
        assert (
            "Found 2 candidates, 0 will be processed (2 skipped - use --force to include)"
            in captured.out
        )
        assert "All files have existing outputs. Use --force to overwrite." in captured.out

    def test_recursive_pre_screening_dry_run_mode(self, tmp_path, capsys):
        """Test that dry-run mode works correctly with pre-screening."""
        # Create input directory structure
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create input files
        (input_dir / "file1.md").write_text("content 1")
        (input_dir / "file2.md").write_text("content 2")

        # Create one existing output file
        (output_dir / "file1.md").write_text("existing output 1")

        # Mock the environment to avoid validation
        with patch.dict("os.environ", {"CEREBRAS_API_KEY": "csk-test-key-12345678"}):
            with patch("cerebrate_file.config.validate_environment"):
                # Run with dry-run mode
                run(
                    input_data=str(input_dir),
                    output_data=str(output_dir),
                    recurse="*.md",
                    force=False,
                    dry_run=True,
                    verbose=True,
                )

        # Check console output
        captured = capsys.readouterr()
        assert (
            "Found 2 candidates, 1 will be processed (1 skipped - use --force to include)"
            in captured.out
        )
        assert "DRY-RUN MODE" in captured.out
        assert "file2.md" in captured.out  # Should show the one file that would be processed

    def test_recursive_pre_screening_in_place_processing(self, tmp_path, capsys):
        """Test pre-screening works correctly with in-place processing."""
        # Create input directory structure
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create input files
        (input_dir / "file1.md").write_text("content 1")
        (input_dir / "file2.md").write_text("content 2")

        # Mock the environment and processing to avoid actual API calls
        with patch.dict("os.environ", {"CEREBRAS_API_KEY": "csk-test-key-12345678"}):
            with patch("cerebrate_file.config.validate_environment"):
                with patch("cerebrate_file.recursive.process_files_parallel") as mock_process:
                    # Configure mock to return empty result
                    mock_result = MagicMock()
                    mock_result.successful = []
                    mock_result.failed = []
                    mock_result.total_input_tokens = 0
                    mock_result.total_output_tokens = 0
                    mock_result.total_time = 0.0
                    mock_process.return_value = mock_result

                    # Run with recursive mode, no output directory (in-place)
                    run(
                        input_data=str(input_dir),
                        output_data=None,  # In-place processing
                        recurse="*.md",
                        force=False,
                        dry_run=False,
                        verbose=True,
                    )

                    # Check that all files were scheduled for processing (in-place doesn't get filtered)
                    mock_process.assert_called_once()
                    call_args = mock_process.call_args[0]
                    file_pairs = call_args[0]  # First argument is file_pairs

                    assert len(file_pairs) == 2

        # Check console output - should not show any skipped files
        captured = capsys.readouterr()
        assert "Found 2 files to process" in captured.out
        assert "skipped" not in captured.out
