#!/usr/bin/env python3
# this_file: tests/test_tokenizer.py

"""Tests for cerebrate_file.tokenizer module."""

from unittest.mock import patch

import pytest

from cerebrate_file.constants import TokenizationError
from cerebrate_file.tokenizer import (
    TokenizerManager,
    decode_tokens_safely,
    encode_text,
    get_tokenizer_manager,
)


def test_tokenizer_manager_initialization():
    """Test TokenizerManager initialization."""
    manager = TokenizerManager(model_name="test-model", strict=False)
    assert manager.model_name == "test-model"
    assert manager.strict is False
    assert manager._initialized is True


def test_tokenizer_manager_fallback_mode():
    """Test TokenizerManager works in fallback mode when qwen-tokenizer not available."""
    with patch("cerebrate_file.tokenizer.logger"):
        manager = TokenizerManager(strict=False)
        # Should work even without qwen-tokenizer
        tokens = manager.encode("Hello world")
        assert isinstance(tokens, list)
        assert len(tokens) > 0


def test_encode_text_function():
    """Test standalone encode_text function."""
    text = "Hello world"
    tokens = encode_text(text)
    assert isinstance(tokens, list)
    assert len(tokens) > 0


def test_decode_tokens_safely_function():
    """Test standalone decode_tokens_safely function."""
    # Test with valid tokens (fallback mode will work)
    tokens = [1, 2, 3, 4, 5]
    decoded = decode_tokens_safely(tokens)
    assert isinstance(decoded, str)


def test_decode_tokens_safely_with_empty_list():
    """Test decode_tokens_safely with empty token list."""
    decoded = decode_tokens_safely([])
    assert decoded == ""


def test_get_tokenizer_manager():
    """Test get_tokenizer_manager function."""
    manager = get_tokenizer_manager()
    assert isinstance(manager, TokenizerManager)


def test_tokenizer_manager_estimate_tokens():
    """Test token estimation functionality."""
    manager = TokenizerManager(strict=False)
    count = manager.estimate_tokens("Hello world")
    assert isinstance(count, int)
    assert count > 0


def test_tokenizer_manager_with_empty_text():
    """Test TokenizerManager with empty text."""
    manager = TokenizerManager(strict=False)

    # Test encoding empty text
    tokens = manager.encode("")
    assert tokens == []

    # Test estimating tokens in empty text
    count = manager.estimate_tokens("")
    assert count == 0


def test_tokenizer_fallback_approximation():
    """Test fallback character-based approximation."""
    manager = TokenizerManager(strict=False)

    # Test with known text to verify fallback works
    text = "A" * 100  # 100 characters
    count = manager.estimate_tokens(text)

    # In fallback mode, should use CHARS_PER_TOKEN_FALLBACK approximation
    assert isinstance(count, int)
    assert count > 0


def test_tokenizer_manager_decode():
    """Test TokenizerManager decode functionality."""
    manager = TokenizerManager(strict=False)

    # Test decoding (should work in fallback mode)
    tokens = [1, 2, 3]
    decoded = manager.decode(tokens)
    assert isinstance(decoded, str)


def test_tokenizer_edge_cases():
    """Test tokenizer edge cases."""
    manager = TokenizerManager(strict=False)

    # Test with empty string
    result = manager.encode("")
    assert isinstance(result, list)
    assert len(result) == 0


def test_tokenizer_properties():
    """Test tokenizer properties."""
    manager = TokenizerManager(strict=False)

    # Test is_available property
    assert isinstance(manager.is_available, bool)

    # Test is_fallback property
    assert isinstance(manager.is_fallback, bool)

    # Test get_info method
    info = manager.get_info()
    assert isinstance(info, dict)


def test_encode_text_with_long_text():
    """Test encoding with longer text."""
    long_text = "This is a longer piece of text " * 100
    tokens = encode_text(long_text)
    assert isinstance(tokens, list)
    assert len(tokens) > 0


def test_encode_text_with_special_characters():
    """Test encoding with special characters."""
    text = "Hello 世界! 🌍 @#$%^&*()"
    tokens = encode_text(text)
    assert isinstance(tokens, list)
    assert len(tokens) > 0
