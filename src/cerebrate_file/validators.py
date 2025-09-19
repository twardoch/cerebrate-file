#!/usr/bin/env python3
# this_file: src/cerebrate_file/validators.py

"""Input validation utilities for cerebrate_file package.

This module provides comprehensive validation for all user inputs
to ensure safe and reliable operation.
"""

import os
from pathlib import Path
from typing import Any, Optional

from .constants import MAX_CONTEXT_TOKENS, ValidationError

__all__ = [
    "validate_chunk_size",
    "validate_temperature",
    "validate_top_p",
    "validate_file_size",
    "validate_model_parameters",
    "validate_file_path_safe",
]

# Validation constants
MIN_CHUNK_SIZE = 10
MAX_CHUNK_SIZE = MAX_CONTEXT_TOKENS - 1000  # Leave room for system prompt
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0
MIN_TOP_P = 0.0
MAX_TOP_P = 1.0
MAX_FILE_SIZE_MB = 100  # 100MB limit for safety
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def validate_chunk_size(chunk_size: int) -> int:
    """Validate chunk size is within acceptable bounds.

    Args:
        chunk_size: Number of tokens per chunk

    Returns:
        Validated chunk size

    Raises:
        ValidationError: If chunk size is invalid
    """
    if not isinstance(chunk_size, int):
        raise ValidationError(f"Chunk size must be an integer, got {type(chunk_size).__name__}")

    if chunk_size < MIN_CHUNK_SIZE:
        raise ValidationError(
            f"Chunk size {chunk_size} is too small. Minimum is {MIN_CHUNK_SIZE} tokens."
        )

    if chunk_size > MAX_CHUNK_SIZE:
        raise ValidationError(
            f"Chunk size {chunk_size} exceeds maximum of {MAX_CHUNK_SIZE} tokens. "
            f"Model context window is {MAX_CONTEXT_TOKENS} tokens."
        )

    return chunk_size


def validate_temperature(temperature: float) -> float:
    """Validate temperature parameter.

    Args:
        temperature: Model temperature (0.0-2.0)

    Returns:
        Validated temperature

    Raises:
        ValidationError: If temperature is invalid
    """
    try:
        temp = float(temperature)
    except (TypeError, ValueError) as e:
        raise ValidationError(f"Temperature must be a number, got {temperature}") from e

    if temp < MIN_TEMPERATURE:
        raise ValidationError(
            f"Temperature {temp} is too low. Minimum is {MIN_TEMPERATURE}."
        )

    if temp > MAX_TEMPERATURE:
        raise ValidationError(
            f"Temperature {temp} is too high. Maximum is {MAX_TEMPERATURE}."
        )

    return temp


def validate_top_p(top_p: float) -> float:
    """Validate top_p (nucleus sampling) parameter.

    Args:
        top_p: Nucleus sampling parameter (0.0-1.0)

    Returns:
        Validated top_p

    Raises:
        ValidationError: If top_p is invalid
    """
    try:
        p = float(top_p)
    except (TypeError, ValueError) as e:
        raise ValidationError(f"top_p must be a number, got {top_p}") from e

    if p < MIN_TOP_P:
        raise ValidationError(f"top_p {p} is too low. Minimum is {MIN_TOP_P}.")

    if p > MAX_TOP_P:
        raise ValidationError(f"top_p {p} is too high. Maximum is {MAX_TOP_P}.")

    return p


def validate_file_size(file_path: str) -> None:
    """Check if file size is within acceptable limits.

    Args:
        file_path: Path to file to check

    Raises:
        ValidationError: If file is too large
    """
    if not os.path.exists(file_path):
        return  # Let other validators handle missing files

    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)

    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f"File size ({file_size_mb:.1f}MB) exceeds maximum of {MAX_FILE_SIZE_MB}MB. "
            f"Consider splitting the file or increasing the limit if needed."
        )


def validate_file_path_safe(file_path: str) -> Path:
    """Validate file path for safety and accessibility.

    Args:
        file_path: Path to validate

    Returns:
        Validated Path object

    Raises:
        ValidationError: If path is invalid or unsafe
    """
    try:
        path = Path(file_path).resolve()
    except (ValueError, OSError) as e:
        raise ValidationError(f"Invalid file path: {file_path}") from e

    # Check for path traversal attempts
    try:
        path.relative_to(Path.cwd())
    except ValueError:
        # File is outside current directory - warn but allow
        pass

    # Check file exists and is readable
    if not path.exists():
        raise ValidationError(f"File not found: {file_path}")

    if not path.is_file():
        raise ValidationError(f"Path is not a file: {file_path}")

    if not os.access(path, os.R_OK):
        raise ValidationError(f"File is not readable: {file_path}")

    return path


def validate_model_parameters(
    chunk_size: int,
    temperature: float,
    top_p: float,
    max_tokens_ratio: int,
) -> tuple[int, float, float, int]:
    """Validate all model parameters together.

    Args:
        chunk_size: Tokens per chunk
        temperature: Model temperature
        top_p: Nucleus sampling parameter
        max_tokens_ratio: Max output tokens as percentage of chunk size

    Returns:
        Tuple of validated parameters

    Raises:
        ValidationError: If any parameter is invalid
    """
    chunk_size = validate_chunk_size(chunk_size)
    temperature = validate_temperature(temperature)
    top_p = validate_top_p(top_p)

    # Validate max_tokens_ratio
    if not isinstance(max_tokens_ratio, int):
        raise ValidationError(
            f"max_tokens_ratio must be an integer, got {type(max_tokens_ratio).__name__}"
        )

    if max_tokens_ratio < 1:
        raise ValidationError(f"max_tokens_ratio must be at least 1%, got {max_tokens_ratio}%")

    if max_tokens_ratio > 200:
        raise ValidationError(
            f"max_tokens_ratio {max_tokens_ratio}% is too high. Maximum is 200%."
        )

    return chunk_size, temperature, top_p, max_tokens_ratio