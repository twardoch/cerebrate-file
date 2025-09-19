#!/usr/bin/env python3
# this_file: src/cerebrate_file/recursive.py

"""Recursive file processing utilities for cerebrate_file package.

This module provides functionality for discovering files recursively using glob patterns,
replicating directory structures, and coordinating parallel file processing.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Any

from loguru import logger

from .models import ProcessingState

__all__ = [
    "find_files_recursive",
    "replicate_directory_structure",
    "process_files_parallel",
    "ProcessingResult",
]


class ProcessingResult:
    """Result container for parallel file processing."""

    def __init__(self) -> None:
        """Initialize processing result container."""
        self.successful: List[Tuple[Path, Path]] = []
        self.failed: List[Tuple[Path, str]] = []
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_time: float = 0.0


def find_files_recursive(
    input_dir: Path,
    pattern: str,
    output_dir: Optional[Path] = None
) -> List[Tuple[Path, Path]]:
    """Find files matching glob pattern and generate output paths.

    Args:
        input_dir: Root directory to search in
        pattern: Glob pattern for file matching (e.g., "*.md", "**/*.txt")
        output_dir: Optional output directory. If None, files are processed in-place

    Returns:
        List of (input_path, output_path) tuples

    Raises:
        ValueError: If input_dir doesn't exist or pattern matches no files
    """
    if not input_dir.exists():
        raise ValueError(f"Input directory does not exist: {input_dir}")

    if not input_dir.is_dir():
        raise ValueError(f"Input path is not a directory: {input_dir}")

    # Find all matching files
    matching_files = list(input_dir.rglob(pattern))

    if not matching_files:
        logger.warning(f"No files found matching pattern '{pattern}' in {input_dir}")
        return []

    logger.info(f"Found {len(matching_files)} files matching '{pattern}'")

    # Generate input/output path pairs
    file_pairs: List[Tuple[Path, Path]] = []

    for input_file in matching_files:
        # Skip directories that might match the pattern
        if input_file.is_dir():
            continue

        # Calculate relative path from input_dir
        relative_path = input_file.relative_to(input_dir)

        if output_dir:
            # Create corresponding output path
            output_file = output_dir / relative_path
        else:
            # In-place processing - output is same as input
            output_file = input_file

        file_pairs.append((input_file, output_file))
        logger.debug(f"Mapped: {input_file} -> {output_file}")

    return file_pairs


def replicate_directory_structure(
    file_pairs: List[Tuple[Path, Path]]
) -> None:
    """Create output directory structure for all file pairs.

    Args:
        file_pairs: List of (input_path, output_path) tuples

    Raises:
        PermissionError: If unable to create directories
    """
    created_dirs = set()

    for _, output_path in file_pairs:
        output_dir = output_path.parent

        # Skip if already created or exists
        if output_dir in created_dirs or output_dir.exists():
            created_dirs.add(output_dir)
            continue

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            created_dirs.add(output_dir)
            logger.debug(f"Created directory: {output_dir}")
        except PermissionError as e:
            logger.error(f"Permission denied creating directory {output_dir}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create directory {output_dir}: {e}")
            raise

    logger.info(f"Created {len(created_dirs)} output directories")


def process_single_file(
    input_path: Path,
    output_path: Path,
    processing_func: Callable[[Path, Path], ProcessingState],
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> Tuple[Path, Path, ProcessingState, Optional[Exception]]:
    """Process a single file with error handling.

    Args:
        input_path: Input file path
        output_path: Output file path
        processing_func: Function to process the file
        progress_callback: Optional callback for progress updates

    Returns:
        Tuple of (input_path, output_path, processing_state, exception)
    """
    try:
        logger.info(f"Processing: {input_path}")

        # Call the processing function
        state = processing_func(input_path, output_path)

        # Report progress if callback provided
        if progress_callback:
            progress_callback(str(input_path), 1)

        logger.info(f"Completed: {input_path} ({state.total_output_tokens} tokens)")
        return input_path, output_path, state, None

    except Exception as e:
        logger.error(f"Failed to process {input_path}: {e}")

        # Create empty state for failed file
        state = ProcessingState()

        # Report progress even for failures
        if progress_callback:
            progress_callback(str(input_path), 1)

        return input_path, output_path, state, e


def process_files_parallel(
    file_pairs: List[Tuple[Path, Path]],
    processing_func: Callable[[Path, Path], ProcessingState],
    workers: int = 4,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> ProcessingResult:
    """Process multiple files in parallel with progress tracking.

    Args:
        file_pairs: List of (input_path, output_path) tuples
        processing_func: Function to process each file
        workers: Number of parallel workers
        progress_callback: Optional callback for progress updates

    Returns:
        ProcessingResult with aggregated statistics
    """
    result = ProcessingResult()

    if not file_pairs:
        logger.warning("No files to process")
        return result

    logger.info(f"Starting parallel processing with {workers} workers for {len(file_pairs)} files")

    # Use ThreadPoolExecutor for I/O-bound operations
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                process_single_file,
                input_path,
                output_path,
                processing_func,
                progress_callback
            ): (input_path, output_path)
            for input_path, output_path in file_pairs
        }

        # Process completed tasks
        for future in as_completed(futures):
            input_path, output_path = futures[future]

            try:
                in_path, out_path, state, exception = future.result()

                if exception:
                    result.failed.append((in_path, str(exception)))
                    logger.warning(f"File failed: {in_path}")
                else:
                    result.successful.append((in_path, out_path))
                    result.total_input_tokens += state.total_input_tokens
                    result.total_output_tokens += state.total_output_tokens
                    result.total_time += state.processing_time

            except Exception as e:
                result.failed.append((input_path, str(e)))
                logger.error(f"Unexpected error processing {input_path}: {e}")

    # Log summary
    logger.info(
        f"Processing complete: {len(result.successful)} successful, "
        f"{len(result.failed)} failed"
    )

    if result.successful:
        avg_time = result.total_time / len(result.successful)
        logger.info(
            f"Total tokens: {result.total_input_tokens} input, "
            f"{result.total_output_tokens} output, "
            f"avg time: {avg_time:.1f}s per file"
        )

    return result