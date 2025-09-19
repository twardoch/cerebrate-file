#!/usr/bin/env python3
# this_file: src/cerebrate_file/ui.py

"""Minimal rich UI components for cerebrate_file package.

This module provides extremely minimalistic terminal UI components using Rich,
specifically designed for the two-row microtable progress display.
No borders, minimal styling, colors allowed.
"""

from typing import Optional
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.text import Text
from loguru import logger

__all__ = ["FileProgressDisplay"]


class FileProgressDisplay:
    """Minimalistic two-row file progress display using Rich.

    Displays progress for file processing in a clean two-row format:
    - Row 1: Input path and progress bar
    - Row 2: Output path and remaining API calls

    No borders, minimal styling, colors allowed.
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize the progress display.

        Args:
            console: Optional Rich console instance. If None, creates a new one.
        """
        self.console = console or Console()
        self.current_task_id: Optional[int] = None
        self.input_path: str = ""
        self.output_path: str = ""
        self.remaining_calls: int = 0

        # Create progress bar with minimal styling
        self.progress = Progress(
            TextColumn("{task.description}", style="bold blue"),
            BarColumn(bar_width=40),
            TextColumn("{task.percentage:>3.0f}%", style="green"),
            console=self.console,
            expand=False,
            transient=False
        )

    def start_file_processing(self, input_path: str, output_path: str, total_chunks: int) -> None:
        """Start processing a new file.

        Args:
            input_path: Path to input file being processed
            output_path: Path where output will be saved
            total_chunks: Total number of chunks to process
        """
        self.input_path = input_path
        self.output_path = output_path
        self.remaining_calls = 0

        # Start the progress tracking
        self.progress.start()

        # Add task for this file
        task_description = f"📄 {input_path}"
        self.current_task_id = self.progress.add_task(
            task_description,
            total=total_chunks
        )

        # Show initial two-row display
        self._update_display()

        logger.debug(f"Started progress tracking for {input_path} ({total_chunks} chunks)")

    def update_progress(self, chunks_completed: int, remaining_calls: int = 0) -> None:
        """Update progress for current file.

        Args:
            chunks_completed: Number of chunks completed so far
            remaining_calls: Remaining API calls available
        """
        if self.current_task_id is None:
            logger.warning("Cannot update progress - no active task")
            return

        self.remaining_calls = remaining_calls

        # Update progress bar
        self.progress.update(self.current_task_id, completed=chunks_completed)

        # Update the two-row display
        self._update_display()

    def finish_file_processing(self) -> None:
        """Finish processing current file and clean up display."""
        if self.current_task_id is not None:
            # Mark task as complete
            self.progress.update(self.current_task_id, completed=self.progress.tasks[self.current_task_id].total)

        # Stop progress tracking
        self.progress.stop()

        # Show final two-row display
        self._show_completion()

        self.current_task_id = None
        logger.debug(f"Finished progress tracking for {self.input_path}")

    def _update_display(self) -> None:
        """Update the two-row display with current status."""
        if not self.input_path:
            return

        # The progress bar itself shows the first row (input path + progress)
        # We need to print the second row separately
        output_text = Text()
        output_text.append("💾 ", style="green")
        output_text.append(self.output_path, style="cyan")

        if self.remaining_calls > 0:
            calls_text = f" ({self.remaining_calls:,} calls remaining)"
            output_text.append(calls_text, style="yellow")

        # Print second row (output path + remaining calls)
        self.console.print(output_text)

    def _show_completion(self) -> None:
        """Show completion status for the file."""
        if not self.output_path:
            return

        completion_text = Text()
        completion_text.append("✅ Saved: ", style="bold green")
        completion_text.append(self.output_path, style="cyan")

        if self.remaining_calls > 0:
            calls_text = f" ({self.remaining_calls:,} calls remaining)"
            completion_text.append(calls_text, style="yellow")

        self.console.print(completion_text)
        self.console.print()  # Add blank line for separation


class MultiFileProgressDisplay:
    """Progress display for multiple files being processed in parallel.

    Manages progress tracking for recursive processing with multiple files.
    Shows overall progress plus individual file progress.
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize multi-file progress display.

        Args:
            console: Optional Rich console instance. If None, creates a new one.
        """
        self.console = console or Console()
        self.file_displays: dict[str, FileProgressDisplay] = {}
        self.total_files: int = 0
        self.completed_files: int = 0

    def start_overall_processing(self, total_files: int) -> None:
        """Start overall processing tracking.

        Args:
            total_files: Total number of files to process
        """
        self.total_files = total_files
        self.completed_files = 0

        # Show overall progress header
        header_text = Text()
        header_text.append("🚀 Processing ", style="bold blue")
        header_text.append(f"{total_files}", style="bold yellow")
        header_text.append(" files recursively", style="bold blue")

        self.console.print(header_text)
        self.console.print()

        logger.info(f"Started multi-file processing for {total_files} files")

    def start_file(self, input_path: str, output_path: str, total_chunks: int) -> None:
        """Start processing a specific file.

        Args:
            input_path: Path to input file
            output_path: Path to output file
            total_chunks: Number of chunks for this file
        """
        display = FileProgressDisplay(self.console)
        self.file_displays[input_path] = display
        display.start_file_processing(input_path, output_path, total_chunks)

    def update_file_progress(self, input_path: str, chunks_completed: int, remaining_calls: int = 0) -> None:
        """Update progress for a specific file.

        Args:
            input_path: Path to file being updated
            chunks_completed: Chunks completed for this file
            remaining_calls: Remaining API calls
        """
        if input_path in self.file_displays:
            self.file_displays[input_path].update_progress(chunks_completed, remaining_calls)

    def finish_file(self, input_path: str) -> None:
        """Finish processing a specific file.

        Args:
            input_path: Path to file that finished processing
        """
        if input_path in self.file_displays:
            self.file_displays[input_path].finish_file_processing()
            del self.file_displays[input_path]

        self.completed_files += 1

        # Show overall progress update
        progress_text = Text()
        progress_text.append(f"📊 Progress: ", style="bold blue")
        progress_text.append(f"{self.completed_files}/{self.total_files}", style="bold yellow")
        progress_text.append(" files completed", style="bold blue")

        self.console.print(progress_text)
        self.console.print()

    def finish_overall_processing(self) -> None:
        """Finish overall processing and show summary."""
        completion_text = Text()
        completion_text.append("🎉 Completed processing ", style="bold green")
        completion_text.append(f"{self.total_files}", style="bold yellow")
        completion_text.append(" files", style="bold green")

        self.console.print(completion_text)
        self.console.print()

        logger.info(f"Completed multi-file processing for {self.total_files} files")