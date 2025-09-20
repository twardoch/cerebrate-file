#!/usr/bin/env python3
# this_file: tests/test_error_recovery.py

"""Tests for cerebrate_file.error_recovery module."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from cerebrate_file.constants import APIError, ValidationError
from cerebrate_file.error_recovery import (
    RecoverableOperation,
    RetryConfig,
    check_optional_dependency,
    format_error_message,
    format_error_with_suggestions,
    load_checkpoint,
    save_checkpoint,
    with_retry,
)


def test_retry_config_default():
    """Test RetryConfig with default values."""
    config = RetryConfig()
    assert config.max_attempts == 3
    assert config.base_delay == 1.0
    assert config.max_delay == 30.0


def test_retry_config_get_delay():
    """Test delay calculation with exponential backoff."""
    config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
    assert config.get_delay(0) == 1.0  # 1 * 2^0
    assert config.get_delay(1) == 2.0  # 1 * 2^1
    assert config.get_delay(2) == 4.0  # 1 * 2^2


def test_retry_config_max_delay():
    """Test that delay is capped at max_delay."""
    config = RetryConfig(base_delay=10.0, max_delay=15.0, jitter=False)
    assert config.get_delay(10) == 15.0  # Should be capped


def test_with_retry_success_first_try():
    """Test successful function call on first try."""
    mock_func = Mock(return_value="success")

    @with_retry
    def test_func():
        return mock_func()

    result = test_func()
    assert result == "success"
    assert mock_func.call_count == 1


def test_with_retry_success_after_failures():
    """Test retry succeeds after transient failures."""
    mock_func = Mock(
        side_effect=[APIError("Temporary error"), APIError("Another error"), "success"]
    )

    @with_retry(config=RetryConfig(max_attempts=3, base_delay=0.01))
    def test_func():
        return mock_func()

    result = test_func()
    assert result == "success"
    assert mock_func.call_count == 3


def test_with_retry_all_attempts_fail():
    """Test that exception is raised after all retries fail."""
    mock_func = Mock(side_effect=APIError("Persistent error"))

    @with_retry(config=RetryConfig(max_attempts=2, base_delay=0.01))
    def test_func():
        return mock_func()

    with pytest.raises(APIError) as exc:
        test_func()

    assert mock_func.call_count == 2
    assert "Suggested fixes" in str(exc.value)


def test_with_retry_non_retryable_error():
    """Test that non-retryable errors are raised immediately."""
    mock_func = Mock(side_effect=ValueError("Not retryable"))

    @with_retry
    def test_func():
        return mock_func()

    with pytest.raises(ValueError):
        test_func()

    assert mock_func.call_count == 1


def test_format_error_with_suggestions_api_error():
    """Test error formatting for API errors."""
    error = APIError("API key invalid")
    enhanced = format_error_with_suggestions(error)

    msg = str(enhanced)
    assert "API key invalid" in msg
    assert "Check your CEREBRAS_API_KEY" in msg
    assert "Suggested fixes" in msg


def test_format_error_with_suggestions_file_error():
    """Test error formatting for file not found errors."""
    error = FileNotFoundError("File not found: test.txt")
    enhanced = format_error_with_suggestions(error)

    msg = str(enhanced)
    assert "test.txt" in msg
    assert "Verify the file path" in msg


def test_format_error_with_suggestions_validation_chunk_size():
    """Test error formatting for chunk size validation errors."""
    error = ValidationError("Chunk size 5 is too small")
    enhanced = format_error_with_suggestions(error)

    msg = str(enhanced)
    assert "chunk size between 10 and 130000" in msg.lower()


def test_format_error_message():
    """Test format_error_message function."""
    error = ConnectionError("Network unreachable")
    msg = format_error_message(error)

    assert "Network unreachable" in msg
    assert "Check your internet connection" in msg


def test_save_and_load_checkpoint():
    """Test saving and loading checkpoints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = {"key": "value", "count": 42}

        # Save checkpoint
        path = save_checkpoint(test_data, checkpoint_dir=tmpdir, checkpoint_name="test")
        assert path.exists()

        # Load checkpoint
        loaded_data = load_checkpoint(checkpoint_dir=tmpdir, checkpoint_name="test")
        assert loaded_data == test_data


def test_load_checkpoint_not_found():
    """Test loading non-existent checkpoint returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_checkpoint(checkpoint_dir=tmpdir, checkpoint_name="nonexistent")
        assert result is None


def test_load_checkpoint_expired():
    """Test that expired checkpoints are not loaded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create an old checkpoint
        checkpoint_data = {
            "timestamp": time.time() - 48 * 3600,  # 48 hours ago
            "data": {"test": "data"},
        }

        checkpoint_path = Path(tmpdir) / "old.json"
        with Path(checkpoint_path).open("w") as f:
            json.dump(checkpoint_data, f)

        # Try to load with 24 hour max age
        result = load_checkpoint(checkpoint_dir=tmpdir, checkpoint_name="old", max_age_hours=24)
        assert result is None


def test_check_optional_dependency_available():
    """Test checking available optional dependency."""
    # json is always available
    available, message = check_optional_dependency("json")
    assert available is True
    assert message is None


def test_check_optional_dependency_missing():
    """Test checking missing optional dependency."""
    available, message = check_optional_dependency("nonexistent_module_xyz")
    assert available is False
    assert "Optional dependency 'nonexistent_module_xyz' not found" in message
    assert "uv add nonexistent_module_xyz" in message


def test_check_optional_dependency_with_feature():
    """Test checking dependency with feature name."""
    available, message = check_optional_dependency(
        "missing_module",
        package_name="special-package",
        feature_name="advanced chunking",
    )
    assert available is False
    assert "for advanced chunking" in message
    assert "uv add special-package" in message


def test_recoverable_operation_no_checkpoint():
    """Test RecoverableOperation without existing checkpoint."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("cerebrate_file.error_recovery.Path") as mock_path:
            mock_path.return_value = Path(tmpdir)

            with RecoverableOperation("test_op") as op:
                assert op.processed_count == 0
                assert op.checkpoint_data == {}

                op.update(item="test1")
                assert op.processed_count == 1


def test_recoverable_operation_with_checkpoint():
    """Test RecoverableOperation resuming from checkpoint."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a checkpoint
        checkpoint_data = {
            "timestamp": time.time(),
            "data": {
                "processed_count": 5,
                "last_item": "item5",
            },
        }

        checkpoint_dir = Path(tmpdir) / ".cerebrate_checkpoints"
        checkpoint_dir.mkdir()
        checkpoint_path = checkpoint_dir / "test_op.json"
        with Path(checkpoint_path).open("w") as f:
            json.dump(checkpoint_data, f)

        # Mock the checkpoint directory
        with patch("cerebrate_file.error_recovery.Path") as mock_path:
            mock_path.return_value = Path(tmpdir)

            # Use operation with existing checkpoint
            with patch("cerebrate_file.error_recovery.load_checkpoint") as mock_load:
                mock_load.return_value = checkpoint_data["data"]

                with RecoverableOperation("test_op") as op:
                    assert op.processed_count == 5
                    assert op.checkpoint_data["last_item"] == "item5"


def test_recoverable_operation_should_skip():
    """Test RecoverableOperation skip logic."""
    with RecoverableOperation("test_op") as op:
        op.checkpoint_data = {"processed_items": ["item1", "item2"]}

        assert op.should_skip("item1") is True
        assert op.should_skip("item3") is False

        # Without checkpoints enabled
        op.enable_checkpoints = False
        assert op.should_skip("item1") is False
