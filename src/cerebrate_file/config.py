#!/usr/bin/env python3
# this_file: src/cerebrate_file/config.py

"""Configuration and validation utilities for cerebrate_file package.

This module handles environment validation, input validation, and logging setup
with user-friendly error messages and comprehensive checks.
"""

import os
import sys
from pathlib import Path

from loguru import logger

from .constants import (
    LOG_FORMAT,
    MAX_CONTEXT_TOKENS,
    VALID_DATA_FORMATS,
    ConfigurationError,
    ValidationError,
)

__all__ = [
    "EnvironmentConfig",
    "get_environment_info",
    "setup_logging",
    "validate_api_key",
    "validate_environment",
    "validate_inputs",
    "validate_recursive_inputs",
]


class EnvironmentConfig:
    """Environment configuration manager."""

    def __init__(self) -> None:
        self.api_key: str | None = None
        self.validated = False
        self._load_environment()

    def _load_environment(self) -> None:
        """Load configuration from environment variables."""
        self.api_key = os.getenv("CEREBRAS_API_KEY")

    def validate(self, strict: bool = True) -> bool:
        """Validate the environment configuration.

        Args:
            strict: If True, exit on validation errors

        Returns:
            True if validation passes

        Raises:
            ConfigurationError: If validation fails and strict=False
        """
        try:
            validate_environment(strict=strict)
            self.validated = True
            return True
        except (ConfigurationError, ValidationError):
            if strict:
                raise
            return False

    def get_api_key(self) -> str:
        """Get the validated API key.

        Returns:
            The API key

        Raises:
            ConfigurationError: If API key is not available or invalid
        """
        if not self.validated:
            self.validate()

        if not self.api_key:
            raise ConfigurationError("CEREBRAS_API_KEY not set")

        return self.api_key


def setup_logging(verbose: bool = False, level: str | None = None) -> None:
    """Configure Loguru logging with appropriate verbosity.

    Args:
        verbose: Enable verbose (DEBUG) logging
        level: Specific log level to use (overrides verbose)
    """
    logger.remove()  # Remove default handler

    log_level = level.upper() if level is not None else "DEBUG" if verbose else "WARNING"

    logger.add(sys.stderr, level=log_level, format=LOG_FORMAT, colorize=True)
    logger.debug(f"Logging configured with level: {log_level}")


def validate_api_key(api_key: str) -> bool:
    """Validate API key format and content.

    Args:
        api_key: The API key to validate

    Returns:
        True if validation passes

    Raises:
        ConfigurationError: If API key is invalid
    """
    if not api_key:
        raise ConfigurationError("API key is empty")

    # Check for common placeholder values
    placeholder_values = {
        "your-api-key",
        "YOUR_API_KEY",
        "test-key",
        "api-key",
        "<your-api-key>",
        "sk-...",  # Common OpenAI-style placeholder
    }

    if api_key in placeholder_values:
        raise ConfigurationError(
            f"API key appears to be a placeholder: {api_key}. "
            "Please replace it with your actual Cerebras API key from https://cloud.cerebras.ai"
        )

    # Format validation
    if not api_key.startswith("csk-"):
        logger.warning("API key doesn't start with 'csk-', this may be incorrect")

    # Length validation (typical Cerebras keys are ~56 characters)
    if len(api_key) < 40:
        logger.warning(f"API key seems short: {len(api_key)} characters (expected ~56)")

    return True


def validate_environment(strict: bool = True) -> None:
    """Validate required environment variables and dependencies.

    Args:
        strict: If True, exit on validation errors

    Raises:
        ConfigurationError: If validation fails and strict=False
    """
    api_key = os.getenv("CEREBRAS_API_KEY")

    if not api_key:
        error_msg = (
            "❌ Error: CEREBRAS_API_KEY environment variable not set\n"
            "\n  To fix this, run one of the following:\n"
            "    export CEREBRAS_API_KEY='your-api-key'  # For current session\n"
            "    echo 'CEREBRAS_API_KEY=your-api-key' >> .env  # Using .env file\n"
            "\n  Get your API key from: https://cloud.cerebras.ai"
        )

        if strict:
            print(error_msg)
            logger.error("CEREBRAS_API_KEY not set")
            sys.exit(1)
        else:
            raise ConfigurationError("CEREBRAS_API_KEY not set")

    try:
        validate_api_key(api_key)
    except ConfigurationError as e:
        if strict:
            print(f"❌ Error: {e}")
            logger.error(str(e))
            sys.exit(1)
        else:
            raise


def validate_inputs(
    input_data: str,
    chunk_size: int,
    sample_size: int,
    max_tokens_ratio: int,
    data_format: str = "text",
    strict: bool = True,
) -> None:
    """Validate CLI input parameters with user-friendly error messages.

    Args:
        input_data: Path to input file
        chunk_size: Maximum tokens per chunk
        sample_size: Continuity sample size
        max_tokens_ratio: Completion budget percentage
        data_format: Chunking strategy
        strict: If True, exit on validation errors

    Raises:
        ValidationError: If validation fails and strict=False
    """
    errors = []

    # Check file existence and accessibility
    try:
        input_path = Path(input_data)
        if not input_path.exists():
            errors.append(f"Input file not found: '{input_data}'")
        elif not input_path.is_file():
            errors.append(f"Path is not a file: '{input_data}'")
        else:
            # Check if file is readable
            try:
                with input_path.open(encoding="utf-8") as f:
                    f.read(1)  # Try reading one character
            except PermissionError:
                errors.append(f"Permission denied reading file: '{input_data}'")
            except Exception as e:
                errors.append(f"Cannot read file '{input_data}': {e}")
    except Exception as e:
        errors.append(f"Invalid input path '{input_data}': {e}")

    # Validate chunk_size
    if chunk_size <= 0:
        errors.append(
            f"chunk_size must be positive, got: {chunk_size}. "
            f"Use a value between 1 and {MAX_CONTEXT_TOKENS:,} tokens."
        )
    elif chunk_size > MAX_CONTEXT_TOKENS:
        errors.append(
            f"chunk_size exceeds model's context limit. "
            f"Maximum allowed: {MAX_CONTEXT_TOKENS:,} tokens, "
            f"you provided: {chunk_size:,} tokens. "
            f"Recommended: 32000 tokens for optimal processing."
        )

    # Validate sample_size
    if sample_size < 0:
        errors.append(
            f"sample_size must be non-negative, got: {sample_size}. "
            f"Use 0 to disable continuity, or a positive value for context size."
        )
    elif chunk_size > 0 and sample_size > chunk_size // 4:
        logger.warning(
            f"Warning: sample_size ({sample_size}) is large relative to "
            f"chunk_size ({chunk_size}). This may reduce effective chunk size."
        )

    # Validate max_tokens_ratio
    if not (1 <= max_tokens_ratio <= 100):
        errors.append(
            f"max_tokens_ratio must be between 1 and 100, got: {max_tokens_ratio}. "
            f"This value represents the completion budget as a percentage of chunk size. "
            f"Use 100 for equal input/output size, or lower for shorter responses."
        )

    # Validate data_format
    if data_format not in VALID_DATA_FORMATS:
        errors.append(
            f"Invalid data_format: '{data_format}'. "
            f"Valid options are: {', '.join(sorted(VALID_DATA_FORMATS))}. "
            f"• text: Line-based chunking (default) "
            f"• semantic: Smart paragraph/sentence boundaries "
            f"• markdown: Respect Markdown structure "
            f"• code: Programming language-aware chunking"
        )

    # Handle errors
    if errors:
        error_msg = "Input validation failed:\n" + "\n".join(f"  • {error}" for error in errors)

        if strict:
            print(f"❌ {error_msg}")
            for error in errors:
                logger.error(error)
            sys.exit(1)
        else:
            raise ValidationError(error_msg)

    logger.debug(f"Input validation passed for: {input_data}")


def get_environment_info() -> dict:
    """Get information about the current environment.

    Returns:
        Dictionary with environment information
    """
    return {
        "python_version": sys.version,
        "platform": sys.platform,
        "has_api_key": bool(os.getenv("CEREBRAS_API_KEY")),
        "working_directory": str(Path.cwd()),
        "user": os.getenv("USER", "unknown"),
    }


def validate_model_parameters(
    temperature: float,
    top_p: float,
    model: str,
    strict: bool = True,
) -> None:
    """Validate model parameters.

    Args:
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        model: Model name
        strict: If True, exit on validation errors

    Raises:
        ValidationError: If validation fails and strict=False
    """
    errors = []

    if not (0.0 <= temperature <= 2.0):
        errors.append(f"temperature must be between 0.0 and 2.0, got: {temperature}")

    if not (0.0 <= top_p <= 1.0):
        errors.append(f"top_p must be between 0.0 and 1.0, got: {top_p}")

    if not model or not isinstance(model, str):
        errors.append(f"model must be a non-empty string, got: {model}")

    if errors:
        error_msg = "Model parameter validation failed:\n" + "\n".join(
            f"  • {error}" for error in errors
        )

        if strict:
            print(f"❌ {error_msg}")
            for error in errors:
                logger.error(error)
            sys.exit(1)
        else:
            raise ValidationError(error_msg)


def validate_recursive_inputs(
    input_data: str,
    recurse: str,
    workers: int,
    output_data: str | None = None,
    strict: bool = True,
) -> None:
    """Validate CLI parameters for recursive processing mode.

    Args:
        input_data: Path to input directory
        recurse: Glob pattern for file matching
        workers: Number of parallel workers
        output_data: Optional output directory path
        strict: If True, exit on validation errors

    Raises:
        ValidationError: If validation fails and strict=False
    """
    errors = []

    # Check input directory existence and accessibility
    try:
        input_path = Path(input_data)
        if not input_path.exists():
            errors.append(f"Input directory not found: '{input_data}'")
        elif not input_path.is_dir():
            errors.append(f"When using --recurse, input_data must be a directory: '{input_data}'")
        else:
            # Check if directory is readable
            try:
                list(input_path.iterdir())
            except PermissionError:
                errors.append(f"Permission denied reading directory: '{input_data}'")
            except Exception as e:
                errors.append(f"Cannot read directory '{input_data}': {e}")
    except Exception as e:
        errors.append(f"Invalid input path '{input_data}': {e}")

    # Validate glob pattern
    if not recurse or not isinstance(recurse, str):
        errors.append(
            "recurse parameter must be a non-empty glob pattern (e.g., '*.md', '**/*.txt')"
        )
    else:
        # Check for common pattern issues
        try:
            # Test if it's a valid glob pattern
            if input_path and input_path.exists():
                test_results = list(input_path.rglob(recurse))
                if not test_results:
                    logger.warning(f"No files found matching pattern '{recurse}' in '{input_data}'")
        except Exception as e:
            errors.append(f"Invalid glob pattern '{recurse}': {e}")

    # Validate workers count
    if not isinstance(workers, int) or workers <= 0:
        errors.append(f"workers must be a positive integer, got: {workers}")
    elif workers > 50:
        logger.warning(
            f"High worker count ({workers}) may cause resource issues. Consider using <= 10."
        )

    # Validate output directory if provided
    if output_data:
        try:
            output_path = Path(output_data)
            if output_path.exists() and not output_path.is_dir():
                errors.append(
                    f"When using --recurse, output_data must be a directory: '{output_data}'"
                )
            elif output_path.exists():
                # Check if directory is writable
                try:
                    test_file = output_path / "test_write_access.tmp"
                    test_file.touch()
                    test_file.unlink()
                except PermissionError:
                    errors.append(f"Permission denied writing to output directory: '{output_data}'")
                except Exception as e:
                    errors.append(f"Cannot write to output directory '{output_data}': {e}")
        except Exception as e:
            errors.append(f"Invalid output path '{output_data}': {e}")

    # Handle errors
    if errors:
        error_msg = "Recursive processing validation failed:\n" + "\n".join(
            f"  • {error}" for error in errors
        )

        if strict:
            print(f"❌ {error_msg}")
            for error in errors:
                logger.error(error)
            sys.exit(1)
        else:
            raise ValidationError(error_msg)

    logger.debug(f"Recursive validation passed for: {input_data} with pattern '{recurse}'")
