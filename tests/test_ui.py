#!/usr/bin/env python3
# this_file: tests/test_ui.py

"""Tests for UI components in cerebrate_file package.

Tests the rich-based progress display components for single and multi-file processing.
"""

import pytest
from io import StringIO
from rich.console import Console

from cerebrate_file.ui import FileProgressDisplay, MultiFileProgressDisplay


class TestFileProgressDisplay:
    """Test FileProgressDisplay class."""

    def test_init_default_console(self):
        """Test initialization with default console."""
        display = FileProgressDisplay()
        assert display.console is not None
        assert display.current_task_id is None
        assert display.input_path == ""
        assert display.output_path == ""
        assert display.remaining_calls == 0

    def test_init_custom_console(self):
        """Test initialization with custom console."""
        custom_console = Console(file=StringIO(), width=80)
        display = FileProgressDisplay(console=custom_console)
        assert display.console is custom_console

    def test_start_file_processing(self):
        """Test starting file processing."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = FileProgressDisplay(console=console)

        input_path = "test_input.txt"
        output_path = "test_output.txt"
        total_chunks = 5

        display.start_file_processing(input_path, output_path, total_chunks)

        assert display.input_path == input_path
        assert display.output_path == output_path
        assert display.current_task_id is not None
        assert display.progress.tasks[display.current_task_id].total == total_chunks

    def test_update_progress(self):
        """Test updating progress."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = FileProgressDisplay(console=console)

        # Start processing first
        display.start_file_processing("input.txt", "output.txt", 10)

        # Update progress
        display.update_progress(chunks_completed=3, remaining_calls=100)

        assert display.remaining_calls == 100
        assert display.progress.tasks[display.current_task_id].completed == 3

    def test_update_progress_no_active_task(self):
        """Test updating progress when no active task."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = FileProgressDisplay(console=console)

        # Try to update without starting
        display.update_progress(chunks_completed=3, remaining_calls=100)

        # Should handle gracefully (logged warning)
        assert display.current_task_id is None

    def test_finish_file_processing(self):
        """Test finishing file processing."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = FileProgressDisplay(console=console)

        # Start and finish processing
        display.start_file_processing("input.txt", "output.txt", 5)
        task_id = display.current_task_id

        display.finish_file_processing()

        assert display.current_task_id is None
        # Task should be marked as complete
        assert display.progress.tasks[task_id].completed == 5

    def test_complete_workflow(self):
        """Test complete workflow from start to finish."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = FileProgressDisplay(console=console)

        # Complete workflow
        display.start_file_processing("test.md", "test_out.md", 3)

        display.update_progress(1, 50)
        display.update_progress(2, 49)
        display.update_progress(3, 48)

        display.finish_file_processing()

        # Check that output was generated
        output_content = output.getvalue()
        assert len(output_content) > 0
        # Should contain file paths and progress indicators
        assert "test.md" in output_content or "test_out.md" in output_content


class TestMultiFileProgressDisplay:
    """Test MultiFileProgressDisplay class."""

    def test_init_default_console(self):
        """Test initialization with default console."""
        display = MultiFileProgressDisplay()
        assert display.console is not None
        assert display.file_displays == {}
        assert display.total_files == 0
        assert display.completed_files == 0

    def test_init_custom_console(self):
        """Test initialization with custom console."""
        custom_console = Console(file=StringIO(), width=80)
        display = MultiFileProgressDisplay(console=custom_console)
        assert display.console is custom_console

    def test_start_overall_processing(self):
        """Test starting overall processing."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = MultiFileProgressDisplay(console=console)

        display.start_overall_processing(total_files=5)

        assert display.total_files == 5
        assert display.completed_files == 0

        # Check output contains progress info
        output_content = output.getvalue()
        assert "5" in output_content
        assert "files" in output_content

    def test_start_file(self):
        """Test starting individual file processing."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = MultiFileProgressDisplay(console=console)

        input_path = "file1.txt"
        output_path = "file1_out.txt"

        display.start_file(input_path, output_path, 3)

        assert input_path in display.file_displays
        file_display = display.file_displays[input_path]
        assert file_display.input_path == input_path
        assert file_display.output_path == output_path

    def test_update_file_progress(self):
        """Test updating progress for specific file."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = MultiFileProgressDisplay(console=console)

        input_path = "file1.txt"
        display.start_file(input_path, "file1_out.txt", 5)

        display.update_file_progress(input_path, chunks_completed=2, remaining_calls=98)

        file_display = display.file_displays[input_path]
        assert file_display.remaining_calls == 98
        assert file_display.progress.tasks[file_display.current_task_id].completed == 2

    def test_update_file_progress_unknown_file(self):
        """Test updating progress for unknown file."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = MultiFileProgressDisplay(console=console)

        # Try to update unknown file - should handle gracefully
        display.update_file_progress("unknown.txt", chunks_completed=1)

        assert "unknown.txt" not in display.file_displays

    def test_finish_file(self):
        """Test finishing individual file processing."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = MultiFileProgressDisplay(console=console)

        input_path = "file1.txt"
        display.start_overall_processing(3)
        display.start_file(input_path, "file1_out.txt", 2)

        assert display.completed_files == 0

        display.finish_file(input_path)

        assert input_path not in display.file_displays
        assert display.completed_files == 1

    def test_finish_overall_processing(self):
        """Test finishing overall processing."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = MultiFileProgressDisplay(console=console)

        display.start_overall_processing(2)
        display.finish_overall_processing()

        # Check output contains completion message
        output_content = output.getvalue()
        assert "Completed" in output_content
        assert "2" in output_content

    def test_complete_multi_file_workflow(self):
        """Test complete multi-file processing workflow."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = MultiFileProgressDisplay(console=console)

        # Start overall processing
        display.start_overall_processing(2)

        # Process first file
        display.start_file("file1.txt", "file1_out.txt", 2)
        display.update_file_progress("file1.txt", 1, 100)
        display.update_file_progress("file1.txt", 2, 99)
        display.finish_file("file1.txt")

        # Process second file
        display.start_file("file2.txt", "file2_out.txt", 3)
        display.update_file_progress("file2.txt", 1, 98)
        display.update_file_progress("file2.txt", 2, 97)
        display.update_file_progress("file2.txt", 3, 96)
        display.finish_file("file2.txt")

        # Finish overall
        display.finish_overall_processing()

        assert display.completed_files == 2
        assert len(display.file_displays) == 0

        # Check that output was generated
        output_content = output.getvalue()
        assert len(output_content) > 0


class TestUIIntegration:
    """Integration tests for UI components."""

    def test_progress_display_renders_without_error(self):
        """Test that progress displays render without throwing exceptions."""
        output = StringIO()
        console = Console(file=output, width=80, height=24)

        # Test single file display
        single_display = FileProgressDisplay(console=console)
        single_display.start_file_processing("long_filename_test.md", "output/long_filename_test_processed.md", 10)

        for i in range(1, 11):
            single_display.update_progress(i, 100 - i)

        single_display.finish_file_processing()

        # Test multi-file display
        multi_display = MultiFileProgressDisplay(console=console)
        multi_display.start_overall_processing(2)

        multi_display.start_file("file1.md", "out/file1.md", 3)
        multi_display.update_file_progress("file1.md", 3, 95)
        multi_display.finish_file("file1.md")

        multi_display.start_file("file2.md", "out/file2.md", 5)
        multi_display.update_file_progress("file2.md", 5, 90)
        multi_display.finish_file("file2.md")

        multi_display.finish_overall_processing()

        # Should have generated output without exceptions
        output_content = output.getvalue()
        assert len(output_content) > 100  # Should have substantial output

    def test_ui_with_edge_case_paths(self):
        """Test UI with edge case file paths."""
        output = StringIO()
        console = Console(file=output, width=80)
        display = FileProgressDisplay(console=console)

        # Test with various path types
        edge_case_paths = [
            ("", "output.txt"),  # Empty input path
            ("input.txt", ""),   # Empty output path
            ("very/long/path/to/some/deeply/nested/file/with/long/name.md",
             "equally/long/output/path/structure/processed_file.md"),  # Long paths
            ("file with spaces.txt", "output with spaces.txt"),  # Spaces in names
            ("file-with-dashes.txt", "output_with_underscores.txt"),  # Special chars
        ]

        for input_path, output_path in edge_case_paths:
            display.start_file_processing(input_path, output_path, 1)
            display.update_progress(1, 50)
            display.finish_file_processing()

        # Should handle all edge cases without exceptions
        output_content = output.getvalue()
        assert len(output_content) > 0