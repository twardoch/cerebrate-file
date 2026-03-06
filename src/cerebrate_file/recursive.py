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

import pathspec
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


def _load_gitignore_spec(directory: Path) -> pathspec.PathSpec | None:
    """Load .gitignore patterns from directory and all parent directories.

    Walks from ``directory`` upward to the filesystem root or a ``.git`` boundary,
    collecting all ``.gitignore`` files.  Patterns are read root-most-first so that
    deeper ``.gitignore`` files take precedence (matching Git's behavior).

    Args:
        directory: Starting directory to search from.

    Returns:
        Compiled PathSpec, or None if no .gitignore files are found.
    """
    gitignore_files: list[Path] = []
    current = directory.resolve()

    while True:
        gitignore_path = current / ".gitignore"
        if gitignore_path.is_file():
            gitignore_files.append(gitignore_path)

        # Stop at .git boundary (repo root)
        if (current / ".git").exists():
            break

        parent = current.parent
        if parent == current:
            # Reached filesystem root
            break
        current = parent

    if not gitignore_files:
        return None

    # Read root-most first so deeper patterns override
    all_lines: list[str] = []
    for gi_path in reversed(gitignore_files):
        try:
            all_lines.extend(gi_path.read_text(encoding="utf-8").splitlines())
        except OSError as e:
            logger.warning(f"Could not read {gi_path}: {e}")
            continue

    spec = pathspec.PathSpec.from_lines("gitwildmatch", all_lines)
    logger.debug(
        f"Loaded .gitignore spec from {len(gitignore_files)} file(s) with {len(all_lines)} patterns"
    )
    return spec


def find_files_recursive(
    input_dir: Path,
    pattern: str,
    output_dir: Path | None = None,
    *,
    unrestricted: bool = False,
) -> list[tuple[Path, Path]]:
    """Find files matching glob pattern and generate output paths.

    Args:
        input_dir: Root directory to search in
        pattern: Glob pattern for file matching (e.g., "*.md", "**/*.{txt,md}")
        output_dir: Optional output directory. If None, files are processed in-place
        unrestricted: If True, skip .gitignore filtering (default: False)

    Returns:
        List of (input_path, output_path) tuples

    Raises:
        ValueError: If input_dir doesn't exist or pattern matches no files
    """
    if not input_dir.exists():
        raise ValueError(f"Input directory does not exist: {input_dir}")

    if not input_dir.is_dir():
        raise ValueError(f"Input path is not a directory: {input_dir}")

    input_dir = input_dir.resolve()
    if output_dir is not None:
        output_dir = output_dir.resolve()

    # Expand brace patterns like **/*.{md,py,js}
    patterns = expand_brace_patterns(pattern)
    logger.debug(f"Using {len(patterns)} pattern(s) for file discovery")

    # Find all matching files across all patterns
    all_matching_files = set()
    for p in patterns:
        try:
            # Always use rglob for recursive search - the function name is find_files_RECURSIVE
            pattern_matches = input_dir.rglob(p)

            file_count = 0
            for match in pattern_matches:
                if match.is_file() and ".git" not in match.relative_to(input_dir).parts:
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

    # Apply .gitignore filtering unless unrestricted
    if not unrestricted:
        spec = _load_gitignore_spec(input_dir)
        if spec:
            before_count = len(matching_files)
            matching_files = [
                f for f in matching_files if not spec.match_file(str(f.relative_to(input_dir)))
            ]
            ignored_count = before_count - len(matching_files)
            if ignored_count > 0:
                logger.info(
                    f"Filtered {ignored_count} file(s) via .gitignore "
                    f"(use --unrestricted to include all)"
                )

    if not matching_files:
        logger.warning(
            f"No files remaining after .gitignore filtering for pattern '{pattern}' in {input_dir}"
        )
        return []

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
        logger.debug("No files to process")
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
