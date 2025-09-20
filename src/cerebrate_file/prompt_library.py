#!/usr/bin/env python3
# this_file: src/cerebrate_file/prompt_library.py

"""Prompt library management for cerebrate_file package.

This module provides functionality for loading prompts from the built-in
prompt library or from user-specified paths.
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

__all__ = ["get_prompt_library_path", "resolve_prompt_file"]


def get_prompt_library_path() -> Path:
    """Get the path to the built-in prompt library.

    Returns:
        Path to the prompts folder within the installed package
    """
    # Get the path to the cerebrate_file package
    import cerebrate_file
    package_dir = Path(cerebrate_file.__file__).parent
    prompt_library = package_dir / "prompts"

    if not prompt_library.exists():
        logger.warning(f"Prompt library directory not found at {prompt_library}")

    return prompt_library


def resolve_prompt_file(file_prompt: str) -> Optional[Path]:
    """Resolve a prompt file path, checking both absolute and library paths.

    Args:
        file_prompt: Path to the prompt file (absolute, relative, or name in library)

    Returns:
        Resolved Path to the prompt file if found, None otherwise
    """
    if not file_prompt:
        return None

    # First, check if the given path exists as-is (absolute or relative)
    direct_path = Path(file_prompt)
    if direct_path.exists() and direct_path.is_file():
        logger.debug(f"Prompt file found at direct path: {direct_path}")
        return direct_path

    # If not found directly, check in the prompt library
    prompt_library = get_prompt_library_path()

    # Try the filename as-is in the library
    library_path = prompt_library / file_prompt
    if library_path.exists() and library_path.is_file():
        logger.info(f"Prompt file found in library: {library_path.name}")
        return library_path

    # Also try just the filename if a path was provided
    # (e.g., if user specified "some/path/prompt.xml", also try "prompt.xml")
    file_name = Path(file_prompt).name
    if file_name != file_prompt:
        library_path = prompt_library / file_name
        if library_path.exists() and library_path.is_file():
            logger.info(f"Prompt file found in library: {library_path.name}")
            return library_path

    # Not found anywhere
    logger.error(f"Prompt file not found: {file_prompt}")
    logger.info(f"Searched in: current path and {prompt_library}")

    # List available prompts in library for user reference
    if prompt_library.exists():
        available = list(prompt_library.glob("*"))
        if available:
            logger.info("Available prompts in library:")
            for prompt in available:
                if prompt.is_file():
                    logger.info(f"  - {prompt.name}")

    return None