#!/usr/bin/env python3
# this_file: tests/test_validators.py

"""Tests for cerebrate_file.validators module."""

import os
import tempfile
from pathlib import Path

import pytest

from cerebrate_file.constants import ValidationError
from cerebrate_file.validators import (
    validate_chunk_size,
    validate_file_path_safe,
    validate_file_size,
    validate_model_parameters,
    validate_temperature,
    validate_top_p,
)


def test_validate_chunk_size_valid():
    """Test chunk size validation with valid values."""
    assert validate_chunk_size(100) == 100
    assert validate_chunk_size(1000) == 1000
    assert validate_chunk_size(32000) == 32000


def test_validate_chunk_size_too_small():
    """Test chunk size validation with too small value."""
    with pytest.raises(ValidationError) as exc:
        validate_chunk_size(5)
    assert "too small" in str(exc.value)


def test_validate_chunk_size_too_large():
    """Test chunk size validation with too large value."""
    with pytest.raises(ValidationError) as exc:
        validate_chunk_size(200000)
    assert "exceeds maximum" in str(exc.value)


def test_validate_chunk_size_invalid_type():
    """Test chunk size validation with invalid type."""
    with pytest.raises(ValidationError) as exc:
        validate_chunk_size("100")
    assert "must be an integer" in str(exc.value)


def test_validate_temperature_valid():
    """Test temperature validation with valid values."""
    assert validate_temperature(0.0) == 0.0
    assert validate_temperature(0.7) == 0.7
    assert validate_temperature(1.5) == 1.5
    assert validate_temperature(2.0) == 2.0


def test_validate_temperature_too_low():
    """Test temperature validation with too low value."""
    with pytest.raises(ValidationError) as exc:
        validate_temperature(-0.1)
    assert "too low" in str(exc.value)


def test_validate_temperature_too_high():
    """Test temperature validation with too high value."""
    with pytest.raises(ValidationError) as exc:
        validate_temperature(2.1)
    assert "too high" in str(exc.value)


def test_validate_temperature_invalid_type():
    """Test temperature validation with invalid type."""
    with pytest.raises(ValidationError) as exc:
        validate_temperature("not_a_number")
    assert "must be a number" in str(exc.value)


def test_validate_top_p_valid():
    """Test top_p validation with valid values."""
    assert validate_top_p(0.0) == 0.0
    assert validate_top_p(0.5) == 0.5
    assert validate_top_p(0.9) == 0.9
    assert validate_top_p(1.0) == 1.0


def test_validate_top_p_too_low():
    """Test top_p validation with too low value."""
    with pytest.raises(ValidationError) as exc:
        validate_top_p(-0.1)
    assert "too low" in str(exc.value)


def test_validate_top_p_too_high():
    """Test top_p validation with too high value."""
    with pytest.raises(ValidationError) as exc:
        validate_top_p(1.1)
    assert "too high" in str(exc.value)


def test_validate_file_size_small_file():
    """Test file size validation with small file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("Small content")
        temp_path = f.name

    try:
        # Should not raise for small files
        validate_file_size(temp_path)
    finally:
        os.unlink(temp_path)


def test_validate_file_size_nonexistent_file():
    """Test file size validation with nonexistent file."""
    # Should not raise for nonexistent files (handled elsewhere)
    validate_file_size("/nonexistent/file.txt")


def test_validate_file_path_safe_valid():
    """Test file path validation with valid file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("Test content")
        temp_path = f.name

    try:
        path = validate_file_path_safe(temp_path)
        assert isinstance(path, Path)
        assert path.exists()
        assert path.is_file()
    finally:
        os.unlink(temp_path)


def test_validate_file_path_safe_nonexistent():
    """Test file path validation with nonexistent file."""
    with pytest.raises(ValidationError) as exc:
        validate_file_path_safe("/nonexistent/file.txt")
    assert "not found" in str(exc.value)


def test_validate_file_path_safe_directory():
    """Test file path validation with directory instead of file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValidationError) as exc:
            validate_file_path_safe(tmpdir)
        assert "not a file" in str(exc.value)


def test_validate_model_parameters_valid():
    """Test combined model parameter validation with valid values."""
    chunk_size, temp, top_p, ratio = validate_model_parameters(
        chunk_size=1000,
        temperature=0.7,
        top_p=0.9,
        max_tokens_ratio=100
    )
    assert chunk_size == 1000
    assert temp == 0.7
    assert top_p == 0.9
    assert ratio == 100


def test_validate_model_parameters_invalid_ratio():
    """Test model parameter validation with invalid ratio."""
    with pytest.raises(ValidationError) as exc:
        validate_model_parameters(
            chunk_size=1000,
            temperature=0.7,
            top_p=0.9,
            max_tokens_ratio=300  # Too high
        )
    assert "too high" in str(exc.value)


def test_validate_model_parameters_multiple_invalid():
    """Test model parameter validation with multiple invalid values."""
    # Should fail on first invalid parameter (chunk_size)
    with pytest.raises(ValidationError) as exc:
        validate_model_parameters(
            chunk_size=5,  # Too small
            temperature=3.0,  # Too high
            top_p=1.5,  # Too high
            max_tokens_ratio=0  # Too low
        )
    assert "too small" in str(exc.value)  # Fails on chunk_size first