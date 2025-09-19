#!/usr/bin/env python3
# this_file: src/cerebrate_file/file_utils.py

"""File I/O and metadata utilities for cerebrate_file package.

This module handles file reading, writing, and frontmatter processing
with atomic operations and error handling.
"""

import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import frontmatter
from loguru import logger

from .constants import REQUIRED_METADATA_FIELDS, FileError
from .tokenizer import encode_text

__all__ = [
    "read_file_safely",
    "write_output_atomically",
    "parse_frontmatter_content",
    "check_metadata_completeness",
    "ensure_parent_directory",
    "backup_file",
    "build_base_prompt",
]


def read_file_safely(file_path: str | Path) -> str:
    """Read file content with error handling.

    Args:
        file_path: Path to the file to read

    Returns:
        File content as string

    Raises:
        FileError: If file cannot be read
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileError(f"File not found: {file_path}")

        if not path.is_file():
            raise FileError(f"Path is not a file: {file_path}")

        content = path.read_text(encoding="utf-8")
        logger.debug(f"Read {len(content)} characters from {file_path}")
        return content

    except FileError:
        raise
    except PermissionError as e:
        raise FileError(f"Permission denied reading file {file_path}: {e}") from e
    except UnicodeDecodeError as e:
        raise FileError(f"Unable to decode file {file_path} as UTF-8: {e}") from e
    except Exception as e:
        raise FileError(f"Failed to read file {file_path}: {e}") from e


def ensure_parent_directory(file_path: str | Path) -> None:
    """Ensure the parent directory of a file exists.

    Args:
        file_path: Path to the file

    Raises:
        FileError: If directory cannot be created
    """
    try:
        path = Path(file_path)
        parent = path.parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created parent directory: {parent}")
    except Exception as e:
        raise FileError(f"Failed to create parent directory for {file_path}: {e}") from e


def backup_file(file_path: str | Path, backup_suffix: str = ".bak") -> Optional[Path]:
    """Create a backup of an existing file.

    Args:
        file_path: Path to the file to backup
        backup_suffix: Suffix to add to backup file

    Returns:
        Path to backup file if created, None if original doesn't exist

    Raises:
        FileError: If backup cannot be created
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return None

        backup_path = path.with_suffix(path.suffix + backup_suffix)
        backup_path.write_bytes(path.read_bytes())
        logger.debug(f"Created backup: {backup_path}")
        return backup_path

    except Exception as e:
        raise FileError(f"Failed to create backup of {file_path}: {e}") from e


def write_output_atomically(
    content: str,
    output_path: str | Path,
    metadata: Optional[Dict[str, Any]] = None,
    create_backup: bool = False,
) -> None:
    """Write output using temporary file for atomicity.

    Args:
        content: Content to write
        output_path: Path to write to
        metadata: Optional frontmatter metadata to include
        create_backup: Whether to backup existing file

    Raises:
        FileError: If writing fails
    """
    try:
        output_path_obj = Path(output_path)
        temp_dir = output_path_obj.parent

        # Ensure parent directory exists
        ensure_parent_directory(output_path_obj)

        # Create backup if requested and file exists
        if create_backup and output_path_obj.exists():
            backup_file(output_path_obj)

        # If metadata is provided, wrap content with frontmatter
        if metadata:
            post = frontmatter.Post(content, **metadata)
            final_content = frontmatter.dumps(post)
        else:
            final_content = content

        # Write to temporary file first
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=temp_dir,
            prefix=f".{output_path_obj.name}.tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(final_content)
            temp_path = Path(temp_file.name)

        # Atomic replacement
        temp_path.replace(output_path_obj)
        logger.info(f"Output written atomically to: {output_path}")

    except Exception as e:
        # Clean up temp file if it exists
        if "temp_path" in locals() and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass  # Best effort cleanup
        raise FileError(f"Failed to write output to {output_path}: {e}") from e


def parse_frontmatter_content(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse frontmatter from content using python-frontmatter.

    Args:
        content: Input text content that may contain frontmatter

    Returns:
        Tuple of (metadata_dict, content_without_frontmatter)
    """
    try:
        post = frontmatter.loads(content)
        metadata = post.metadata if post.metadata else {}
        content_only = post.content if post.content else content

        logger.debug(
            f"Frontmatter parsed: {len(metadata)} metadata fields, "
            f"{len(content_only)} content chars"
        )
        return metadata, content_only

    except Exception as e:
        logger.warning(f"Frontmatter parsing failed: {e}, treating as plain content")
        return {}, content


def check_metadata_completeness(metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Check if metadata contains all required fields.

    Args:
        metadata: Parsed metadata dictionary

    Returns:
        Tuple of (is_complete, missing_fields_list)
    """
    missing_fields = []
    for field in REQUIRED_METADATA_FIELDS:
        if field not in metadata or not metadata[field]:
            missing_fields.append(field)

    is_complete = len(missing_fields) == 0
    logger.debug(f"Metadata completeness: {is_complete}, missing: {missing_fields}")

    return is_complete, missing_fields


def validate_file_path(file_path: str | Path, must_exist: bool = True) -> Path:
    """Validate a file path and return as Path object.

    Args:
        file_path: Path to validate
        must_exist: Whether the file must already exist

    Returns:
        Validated Path object

    Raises:
        FileError: If validation fails
    """
    try:
        path = Path(file_path)

        if must_exist:
            if not path.exists():
                raise FileError(f"File not found: {file_path}")
            if not path.is_file():
                raise FileError(f"Path is not a file: {file_path}")

        return path

    except FileError:
        raise
    except Exception as e:
        raise FileError(f"Invalid file path {file_path}: {e}") from e


def get_file_info(file_path: str | Path) -> Dict[str, Any]:
    """Get information about a file.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with file information

    Raises:
        FileError: If file cannot be accessed
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileError(f"File not found: {file_path}")

        stat = path.stat()
        return {
            "path": str(path.absolute()),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "readable": path.is_file() and path.stat().st_mode & 0o444,
            "writable": path.parent.stat().st_mode & 0o222 if path.parent.exists() else False,
        }

    except FileError:
        raise
    except Exception as e:
        raise FileError(f"Failed to get file info for {file_path}: {e}") from e


def build_base_prompt(
    file_prompt: Optional[str], text_prompt: Optional[str]
) -> Tuple[str, int]:
    """Assemble base prompt from file and text components.

    Args:
        file_prompt: Path to file containing initial instructions
        text_prompt: Freeform instruction text to append after file_prompt

    Returns:
        Tuple of (prompt_text, token_count)
    """
    base_prompt = ""

    # Read file prompt if provided
    if file_prompt:
        if not Path(file_prompt).exists():
            logger.error(f"Prompt file not found: {file_prompt}")
            sys.exit(1)
        base_prompt += read_file_safely(file_prompt)
        logger.debug(f"Loaded file prompt from: {file_prompt}")

    # Add separator (always two newlines per spec)
    base_prompt += "\n\n"

    # Append text prompt if provided
    if text_prompt:
        base_prompt += text_prompt
        logger.debug(f"Added text prompt: {text_prompt[:50]}...")

    # Calculate token count
    token_count = len(encode_text(base_prompt))
    logger.info(f"Base prompt assembled: {token_count} tokens")

    return base_prompt, token_count