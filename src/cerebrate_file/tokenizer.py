#!/usr/bin/env python3
# this_file: src/cerebrate_file/tokenizer.py

"""Text tokenization utilities for cerebrate_file package.

This module handles text encoding and decoding with fallback mechanisms
for when the qwen-tokenizer dependency is not available.
"""

from loguru import logger

from .constants import CHARS_PER_TOKEN_FALLBACK, TokenizationError

__all__ = [
    "TokenizerManager",
    "decode_tokens_safely",
    "encode_text",
    "get_tokenizer_manager",
]


class TokenizerManager:
    """Manages tokenizer initialization and provides fallback mechanisms.

    This class handles the optional qwen-tokenizer dependency gracefully,
    providing character-based approximations when the actual tokenizer
    is not available.
    """

    def __init__(self, model_name: str = "qwen-max", strict: bool = False) -> None:
        """Initialize the tokenizer manager.

        Args:
            model_name: Name of the tokenizer model to use
            strict: If True, raise exception if tokenizer unavailable
        """
        self.model_name = model_name
        self.strict = strict
        self._tokenizer: object | None = None
        self._initialized = False
        self._initialize_tokenizer()

    def _initialize_tokenizer(self) -> None:
        """Initialize the qwen tokenizer with fallback handling."""
        try:
            from qwen_tokenizer import get_tokenizer

            # Initialize tokenizer for qwen models
            self._tokenizer = get_tokenizer(self.model_name)
            self._initialized = True
            logger.debug(f"Qwen tokenizer initialized with model: {self.model_name}")

        except ImportError:
            error_msg = "qwen-tokenizer not available. Install with: uv add qwen-tokenizer"
            if self.strict:
                logger.error(error_msg)
                raise TokenizationError(error_msg) from None
            else:
                logger.warning(f"{error_msg}. Using character-based fallback.")
                self._tokenizer = None
                self._initialized = True

        except Exception as e:
            error_msg = f"Failed to initialize qwen tokenizer: {e}"
            if self.strict:
                logger.error(error_msg)
                raise TokenizationError(error_msg) from e
            else:
                logger.warning(f"{error_msg}. Falling back to character-based approximation")
                self._tokenizer = None
                self._initialized = True

    @property
    def is_available(self) -> bool:
        """Check if the actual tokenizer is available."""
        return self._tokenizer is not None

    @property
    def is_fallback(self) -> bool:
        """Check if we're using fallback tokenization."""
        return self._tokenizer is None

    def encode(self, text: str) -> list[int]:
        """Encode text to tokens with fallback handling.

        Args:
            text: Text to encode

        Returns:
            List of token IDs

        Raises:
            TokenizationError: If encoding fails and strict mode is enabled
        """
        if not self._initialized:
            raise TokenizationError("Tokenizer not initialized")

        if self._tokenizer is None:
            # Character-based fallback: approximate chars per token
            return list(range(len(text) // CHARS_PER_TOKEN_FALLBACK + 1))

        try:
            return self._tokenizer.encode(text)
        except Exception as e:
            error_msg = f"Tokenizer encode failed: {e}"
            if self.strict:
                logger.error(error_msg)
                raise TokenizationError(error_msg) from e
            else:
                logger.warning(f"{error_msg}, using character fallback")
                return list(range(len(text) // CHARS_PER_TOKEN_FALLBACK + 1))

    def decode(self, tokens: list[int]) -> str:
        """Decode tokens back to text with fallback handling.

        Args:
            tokens: List of token IDs

        Returns:
            Decoded text string

        Raises:
            TokenizationError: If decoding fails and strict mode is enabled
        """
        if not self._initialized:
            raise TokenizationError("Tokenizer not initialized")

        if self._tokenizer is None:
            return "[NO_TOKENIZER_FALLBACK]"

        try:
            # Check if tokenizer has decode method
            if hasattr(self._tokenizer, "decode"):
                return self._tokenizer.decode(tokens)
            else:
                # Fallback: this is a limitation we'll handle gracefully
                logger.debug("Tokenizer decode not available, using fallback")
                return "[DECODED_TOKENS_FALLBACK]"
        except Exception as e:
            error_msg = f"Token decode failed: {e}"
            if self.strict:
                logger.error(error_msg)
                raise TokenizationError(error_msg) from e
            else:
                logger.warning(f"{error_msg}, using fallback")
                return "[DECODE_ERROR_FALLBACK]"

    def estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens in text.

        This provides a quick approximation without full tokenization.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        if self._tokenizer is None:
            return len(text) // CHARS_PER_TOKEN_FALLBACK + 1
        else:
            # For real tokenizer, we still do actual encoding for accuracy
            return len(self.encode(text))

    def get_info(self) -> dict:
        """Get information about the tokenizer state."""
        return {
            "model_name": self.model_name,
            "is_available": self.is_available,
            "is_fallback": self.is_fallback,
            "strict_mode": self.strict,
            "initialized": self._initialized,
        }


# Global tokenizer manager instance
_global_tokenizer: TokenizerManager | None = None


def get_tokenizer_manager() -> TokenizerManager:
    """Get the global tokenizer manager instance."""
    global _global_tokenizer
    if _global_tokenizer is None:
        _global_tokenizer = TokenizerManager()
    return _global_tokenizer


def encode_text(text: str) -> list[int]:
    """Encode text to tokens with fallback handling.

    This is a convenience function that uses the global tokenizer manager.

    Args:
        text: Text to encode

    Returns:
        List of token IDs
    """
    return get_tokenizer_manager().encode(text)


def decode_tokens_safely(tokens: list[int]) -> str:
    """Decode tokens back to text with fallback handling.

    This is a convenience function that uses the global tokenizer manager.

    Args:
        tokens: List of token IDs

    Returns:
        Decoded text string
    """
    return get_tokenizer_manager().decode(tokens)
