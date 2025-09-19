#!/usr/bin/env python3
# this_file: src/cerebrate_file/error_recovery.py

"""Error recovery and resilience utilities for cerebrate_file package.

This module provides automatic retry mechanisms, helpful error messages,
and recovery strategies for transient failures.
"""

import functools
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from .constants import APIError, ChunkingError, ValidationError

__all__ = [
    "with_retry",
    "format_error_message",
    "save_checkpoint",
    "load_checkpoint",
    "check_optional_dependency",
    "RetryConfig",
]

T = TypeVar("T")

class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number.

        Args:
            attempt: Attempt number (0-based)

        Returns:
            Delay in seconds
        """
        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
        if self.jitter:
            import random
            delay *= (0.5 + random.random())  # Add 0-50% jitter
        return delay


def with_retry(
    func: Optional[Callable] = None,
    *,
    config: Optional[RetryConfig] = None,
    retryable_errors: tuple = (APIError, ConnectionError, TimeoutError),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable:
    """Decorator to add retry logic to functions.

    Args:
        func: Function to wrap
        config: Retry configuration
        retryable_errors: Tuple of exception types to retry on
        on_retry: Callback function called on each retry

    Returns:
        Wrapped function with retry logic
    """
    if config is None:
        config = RetryConfig()

    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> T:
            last_error = None

            for attempt in range(config.max_attempts):
                try:
                    return f(*args, **kwargs)
                except retryable_errors as e:
                    last_error = e

                    if attempt < config.max_attempts - 1:
                        delay = config.get_delay(attempt)

                        if on_retry:
                            on_retry(e, attempt + 1)
                        else:
                            print(f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}")
                            print(f"Retrying in {delay:.1f} seconds...")

                        time.sleep(delay)
                    else:
                        # Final attempt failed
                        raise format_error_with_suggestions(e)

            # Should not reach here, but handle it
            if last_error:
                raise last_error

        return wrapper

    if func is None:
        return decorator
    return decorator(func)


def format_error_with_suggestions(error: Exception) -> Exception:
    """Format error with helpful suggestions for resolution.

    Args:
        error: Original exception

    Returns:
        Enhanced exception with suggestions
    """
    error_type = type(error).__name__
    original_msg = str(error)

    suggestions = []

    # API-related errors
    if isinstance(error, APIError) or "API" in original_msg:
        suggestions.extend([
            "Check your CEREBRAS_API_KEY environment variable is set correctly",
            "Verify your internet connection is stable",
            "Try again in a few moments (API might be temporarily unavailable)",
            "Check if you have sufficient API credits/quota",
        ])

    # File-related errors
    elif isinstance(error, FileNotFoundError):
        suggestions.extend([
            "Verify the file path is correct",
            "Check if the file exists: use 'ls' to list files",
            "Ensure you have read permissions for the file",
        ])

    # Permission errors
    elif isinstance(error, PermissionError):
        suggestions.extend([
            "Check file permissions with 'ls -la'",
            "Try running with appropriate permissions",
            "Verify the output directory is writable",
        ])

    # Validation errors
    elif isinstance(error, ValidationError):
        if "chunk_size" in original_msg.lower():
            suggestions.extend([
                "Use a chunk size between 10 and 130000 tokens",
                "Try the default chunk size: --chunk-size 32000",
            ])
        elif "temperature" in original_msg.lower():
            suggestions.extend([
                "Use a temperature between 0.0 and 2.0",
                "Try the default temperature: --temperature 0.7",
            ])
        elif "file size" in original_msg.lower():
            suggestions.extend([
                "Split large files into smaller parts",
                "Use a text editor to extract relevant sections",
                "Consider increasing the file size limit if needed",
            ])

    # Connection errors
    elif isinstance(error, (ConnectionError, TimeoutError)):
        suggestions.extend([
            "Check your internet connection",
            "Try using a different network",
            "Verify firewall/proxy settings",
            "Wait a few moments and try again",
        ])

    # Format the enhanced error message
    if suggestions:
        enhanced_msg = f"{original_msg}\n\nSuggested fixes:\n"
        for i, suggestion in enumerate(suggestions, 1):
            enhanced_msg += f"  {i}. {suggestion}\n"

        # Create new exception with enhanced message
        new_error = type(error)(enhanced_msg)
        new_error.__cause__ = error
        return new_error

    return error


def format_error_message(error: Exception) -> str:
    """Format error message with helpful context.

    Args:
        error: Exception to format

    Returns:
        Formatted error message
    """
    enhanced_error = format_error_with_suggestions(error)
    return str(enhanced_error)


def save_checkpoint(
    data: dict,
    checkpoint_dir: str = ".cerebrate_checkpoints",
    checkpoint_name: str = "checkpoint",
) -> Path:
    """Save processing checkpoint for recovery.

    Args:
        data: Data to save in checkpoint
        checkpoint_dir: Directory for checkpoints
        checkpoint_name: Name of checkpoint file

    Returns:
        Path to saved checkpoint
    """
    checkpoint_path = Path(checkpoint_dir)
    checkpoint_path.mkdir(exist_ok=True, parents=True)

    file_path = checkpoint_path / f"{checkpoint_name}.json"

    # Add metadata
    checkpoint_data = {
        "timestamp": time.time(),
        "data": data,
    }

    # Save atomically
    temp_path = file_path.with_suffix(".tmp")
    with open(temp_path, "w") as f:
        json.dump(checkpoint_data, f, indent=2)

    temp_path.replace(file_path)
    return file_path


def load_checkpoint(
    checkpoint_dir: str = ".cerebrate_checkpoints",
    checkpoint_name: str = "checkpoint",
    max_age_hours: float = 24,
) -> Optional[dict]:
    """Load processing checkpoint if available and recent.

    Args:
        checkpoint_dir: Directory containing checkpoints
        checkpoint_name: Name of checkpoint file
        max_age_hours: Maximum age of checkpoint in hours

    Returns:
        Checkpoint data if available and valid, None otherwise
    """
    checkpoint_path = Path(checkpoint_dir) / f"{checkpoint_name}.json"

    if not checkpoint_path.exists():
        return None

    try:
        with open(checkpoint_path) as f:
            checkpoint_data = json.load(f)

        # Check age
        age_hours = (time.time() - checkpoint_data["timestamp"]) / 3600
        if age_hours > max_age_hours:
            return None

        return checkpoint_data["data"]
    except (json.JSONDecodeError, KeyError, IOError):
        return None


def check_optional_dependency(
    module_name: str,
    package_name: Optional[str] = None,
    feature_name: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """Check if optional dependency is available with helpful message.

    Args:
        module_name: Python module to import
        package_name: Package name for installation (if different from module)
        feature_name: Feature that requires this dependency

    Returns:
        Tuple of (is_available, help_message)
    """
    if package_name is None:
        package_name = module_name

    try:
        __import__(module_name)
        return True, None
    except ImportError:
        feature_desc = f" for {feature_name}" if feature_name else ""

        message = (
            f"Optional dependency '{module_name}' not found{feature_desc}.\n"
            f"To enable this feature, install it with:\n"
            f"  uv add {package_name}\n"
            f"Or continue without this feature."
        )
        return False, message


class RecoverableOperation:
    """Context manager for operations that support checkpointing."""

    def __init__(
        self,
        operation_name: str,
        checkpoint_interval: int = 10,
        enable_checkpoints: bool = True,
    ):
        """Initialize recoverable operation.

        Args:
            operation_name: Name for checkpoint files
            checkpoint_interval: Save checkpoint every N items
            enable_checkpoints: Whether to enable checkpointing
        """
        self.operation_name = operation_name
        self.checkpoint_interval = checkpoint_interval
        self.enable_checkpoints = enable_checkpoints
        self.processed_count = 0
        self.checkpoint_data = {}

    def __enter__(self):
        """Enter context and load any existing checkpoint."""
        if self.enable_checkpoints:
            self.checkpoint_data = load_checkpoint(
                checkpoint_name=self.operation_name
            ) or {}
            if self.checkpoint_data:
                self.processed_count = self.checkpoint_data.get("processed_count", 0)
                print(f"Resuming from checkpoint: {self.processed_count} items already processed")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up checkpoints on successful completion."""
        if exc_type is None and self.enable_checkpoints:
            # Operation completed successfully, clean up checkpoint
            checkpoint_path = Path(".cerebrate_checkpoints") / f"{self.operation_name}.json"
            if checkpoint_path.exists():
                checkpoint_path.unlink()

    def update(self, **kwargs):
        """Update checkpoint data and save if needed."""
        self.checkpoint_data.update(kwargs)
        self.processed_count += 1

        if self.enable_checkpoints and self.processed_count % self.checkpoint_interval == 0:
            self.checkpoint_data["processed_count"] = self.processed_count
            save_checkpoint(self.checkpoint_data, checkpoint_name=self.operation_name)

    def should_skip(self, item_id: Any) -> bool:
        """Check if item should be skipped based on checkpoint."""
        if not self.enable_checkpoints:
            return False

        processed_items = self.checkpoint_data.get("processed_items", [])
        return item_id in processed_items