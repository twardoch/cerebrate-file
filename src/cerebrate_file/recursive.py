#!/usr/bin/env python3
# this_file: src/cerebrate_file/recursive.py

"""Recursive file processing utilities for cerebrate_file package.

This module provides functionality for discovering files recursively using glob patterns,
replicating directory structures, and coordinating parallel file processing.
"""

import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from loguru import logger

from .models import ProcessingState

__all__ = [
    "ProcessingResult",
    "expand_brace_patterns",
    "find_files_recursive",
    "pre_screen_files",
    "process_files_parallel",
    "replicate_directory_structure",
]


class ProcessingResult:
    """Result container for parallel file processing."""

    def __init__(self) -> None:
        """Initialize processing result container."""
        self.successful: list[tuple[Path, Path]] = []
        self.failed: list[tuple[Path, str]] = []
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_time: float = 0.0


def pre_screen_files(file_pairs: list[tuple[Path, Path]], force: bool) -> list[tuple[Path, Path]]:
    """Pre-screen file pairs, removing those with existing outputs if force=False.

    Args:
        file_pairs: List of (input_path, output_path) tuples
        force: If True, return all pairs; if False, filter existing outputs

    Returns:
        Filtered list of file pairs
    """
    if force:
        logger.debug("Force mode enabled, skipping pre-screening")
        return file_pairs

    if not file_pairs:
        return file_pairs

    from .file_utils import output_file_exists

    original_count = len(file_pairs)
    filtered_pairs = []
    skipped_count = 0

    logger.debug(f"Starting pre-screening of {original_count} file pairs")

    for input_path, output_path in file_pairs:
        if output_file_exists(input_path, output_path):
            logger.debug(f"Skipping {input_path} -> {output_path}: output file exists")
            skipped_count += 1
        else:
            filtered_pairs.append((input_path, output_path))

    logger.info(
        f"Pre-screening complete: {len(filtered_pairs)} files to process, "
        f"{skipped_count} skipped (existing outputs)"
    )

    return filtered_pairs


def expand_brace_patterns(pattern: str) -> list[str]:
    """Expand brace patterns like '*.{md,py,js}' into separate patterns.

    Args:
        pattern: Glob pattern that may contain brace expansion like '**/*.{md,py,js}'

    Returns:
        List of expanded patterns, or single pattern if no braces found

    Examples:
        expand_brace_patterns('*.{md,py}') -> ['*.md', '*.py']
        expand_brace_patterns('**/*.{txt,md,py,js}') -> ['**/*.txt', '**/*.md', '**/*.py', '**/*.js']
        expand_brace_patterns('*.md') -> ['*.md']
    """
    # Find brace pattern like {ext1,ext2,ext3}
    brace_match = re.search(r"\{([^}]+)\}", pattern)

    if not brace_match:
        return [pattern]

    # Extract the options inside braces
    options = [opt.strip() for opt in brace_match.group(1).split(",")]

    # Create base pattern with placeholder
    base_pattern = pattern[: brace_match.start()] + "{}" + pattern[brace_match.end() :]

    # Generate all expanded patterns
    expanded = [base_pattern.format(opt) for opt in options if opt]

    logger.debug(f"Expanded pattern '{pattern}' into {len(expanded)} patterns: {expanded}")

    return expanded


def find_files_recursive(
    input_dir: Path, pattern: str, output_dir: Path | None = None
) -> list[tuple[Path, Path]]:
    """Find files matching glob pattern and generate output paths.

    Args:
        input_dir: Root directory to search in
        pattern: Glob pattern for file matching (e.g., "*.md", "**/*.{txt,md}")
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

    # Expand brace patterns like **/*.{md,py,js}
    patterns = expand_brace_patterns(pattern)
    logger.debug(f"Using {len(patterns)} pattern(s) for file discovery")

    # Find all matching files across all patterns
    all_matching_files = set()
    for p in patterns:
        try:
            pattern_matches = input_dir.rglob(p)

            file_count = 0
            for match in pattern_matches:
                if match.is_file():  # Only include files, not directories
                    all_matching_files.add(match)
                    file_count += 1

            logger.debug(f"Pattern '{p}' found {file_count} file matches")
        except Exception as e:
            logger.warning(f"Error processing pattern '{p}': {e}")
            continue

    matching_files = list(all_matching_files)

    if not matching_files:
        logger.warning(f"No files found matching pattern '{pattern}' in {input_dir}")
        return []

    logger.info(f"Found {len(matching_files)} files matching '{pattern}'")

    # Generate input/output path pairs
    file_pairs: list[tuple[Path, Path]] = []

    for input_file in matching_files:
        # Calculate relative path from input_dir
        relative_path = input_file.relative_to(input_dir)

        output_file = output_dir / relative_path if output_dir else input_file

        file_pairs.append((input_file, output_file))
        logger.debug(f"Mapped: {input_file} -> {output_file}")

    return file_pairs


def replicate_directory_structure(file_pairs: list[tuple[Path, Path]]) -> None:
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
    progress_callback: Callable[[str, int], None] | None = None,
) -> tuple[Path, Path, ProcessingState, Exception | None]:
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
    file_pairs: list[tuple[Path, Path]],
    processing_func: Callable[[Path, Path], ProcessingState],
    workers: int = 4,
    progress_callback: Callable[[str, int], None] | None = None,
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
                process_single_file, input_path, output_path, processing_func, progress_callback
            ): (input_path, output_path)
            for input_path, output_path in file_pairs
        }

        # Process completed tasks
        for future in as_completed(futures):
            input_path, _output_path = futures[future]

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
        f"Processing complete: {len(result.successful)} successful, {len(result.failed)} failed"
    )

    if result.successful:
        avg_time = result.total_time / len(result.successful)
        logger.info(
            f"Total tokens: {result.total_input_tokens} input, "
            f"{result.total_output_tokens} output, "
            f"avg time: {avg_time:.1f}s per file"
        )

    return result
