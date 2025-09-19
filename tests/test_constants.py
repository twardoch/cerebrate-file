#!/usr/bin/env python3
# this_file: tests/test_constants.py

"""Tests for cerebrate_file.constants module."""

import pytest
from cerebrate_file.constants import (
    APIError,
    ChunkingError,
    CODE_BOUNDARY_PATTERNS,
    COMPILED_BOUNDARY_PATTERNS,
    DEFAULT_CHUNK_SIZE,
    MAX_CONTEXT_TOKENS,
    MAX_OUTPUT_TOKENS,
    METADATA_SCHEMA,
    REQUIRED_METADATA_FIELDS,
    TokenizationError,
    ValidationError,
    CerebrateError,
)


def test_constants_values():
    """Test that constants have expected values."""
    assert MAX_CONTEXT_TOKENS == 131000
    assert MAX_OUTPUT_TOKENS == 40000
    assert DEFAULT_CHUNK_SIZE == 32000


def test_required_metadata_fields():
    """Test required metadata fields."""
    expected_fields = {"title", "author", "id", "type", "date"}
    assert REQUIRED_METADATA_FIELDS == expected_fields


def test_metadata_schema():
    """Test metadata schema structure."""
    assert isinstance(METADATA_SCHEMA, dict)
    assert METADATA_SCHEMA["type"] == "object"
    assert "properties" in METADATA_SCHEMA
    assert "required" in METADATA_SCHEMA
    assert set(METADATA_SCHEMA["required"]) == REQUIRED_METADATA_FIELDS


def test_error_classes():
    """Test error classes."""
    assert issubclass(APIError, CerebrateError)
    assert issubclass(ChunkingError, CerebrateError)
    assert issubclass(TokenizationError, CerebrateError)
    assert issubclass(ValidationError, CerebrateError)


def test_boundary_patterns():
    """Test code boundary patterns."""
    assert isinstance(CODE_BOUNDARY_PATTERNS, list)
    assert len(CODE_BOUNDARY_PATTERNS) > 0
    assert isinstance(COMPILED_BOUNDARY_PATTERNS, list)
    assert len(COMPILED_BOUNDARY_PATTERNS) == len(CODE_BOUNDARY_PATTERNS)


def test_cerebrate_error():
    """Test CerebrateError exception class."""
    error = CerebrateError("test message")
    assert str(error) == "test message"
    assert isinstance(error, Exception)


def test_specific_error_classes():
    """Test specific error classes."""
    api_error = APIError("API failed")
    assert str(api_error) == "API failed"
    assert isinstance(api_error, CerebrateError)

    chunk_error = ChunkingError("Chunking failed")
    assert str(chunk_error) == "Chunking failed"
    assert isinstance(chunk_error, CerebrateError)