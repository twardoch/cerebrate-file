#!/usr/bin/env python3
# this_file: src/cerebrate_file/continuity.py

"""Keeps context flowing between chunks.

Stitches chunks together by passing the tail end of the last input/output
into the next request. Prevents the model from losing the plot.
"""

from loguru import logger

from .constants import CONTINUITY_TEMPLATE, MAX_CONTEXT_TOKENS
from .tokenizer import decode_tokens_safely, encode_text

__all__ = [
    "ContinuityManager",
    "build_continuity_block",
    "extract_continuity_examples",
    "fit_continuity_to_budget",
]


class ContinuityManager:
    """Holds onto the previous chunk so the next one makes sense."""

    def __init__(self, sample_size: int = 200) -> None:
        """Initialize the continuity manager.

        Args:
            sample_size: Number of tokens to use for continuity examples
        """
        self.sample_size = sample_size
        self.prev_input_text = ""
        self.prev_output_text = ""
        self.prev_input_tokens: list[int] = []
        self.prev_output_tokens: list[int] = []

    def update(
        self,
        input_text: str,
        output_text: str,
        input_tokens: list[int] | None = None,
        output_tokens: list[int] | None = None,
    ) -> None:
        """Save the input and output from the chunk we just processed.

        Args:
            input_text: The input text that was processed
            output_text: The output text generated
            input_tokens: Optional token list for input
            output_tokens: Optional token list for output
        """
        self.prev_input_text = input_text
        self.prev_output_text = output_text

        if input_tokens is not None:
            self.prev_input_tokens = input_tokens
        else:
            self.prev_input_tokens = encode_text(input_text)

        if output_tokens is not None:
            self.prev_output_tokens = output_tokens
        else:
            self.prev_output_tokens = encode_text(output_text)

    def has_context(self) -> bool:
        """Do we have a previous chunk to draw context from?"""
        return bool(self.prev_input_tokens and self.prev_output_tokens)

    def get_continuity_block(self) -> str | None:
        """Build the continuity prompt block using the saved context.

        Returns:
            Formatted continuity block or None if no context
        """
        if not self.has_context():
            return None

        input_example = extract_continuity_examples(
            self.prev_input_text, self.prev_input_tokens, self.sample_size
        )

        output_example = extract_continuity_examples(
            self.prev_output_text, self.prev_output_tokens, self.sample_size
        )

        if not input_example or not output_example:
            return None

        return build_continuity_block(input_example, output_example)

    def get_fitted_continuity(
        self, base_input_tokens: int, max_input_tokens: int = MAX_CONTEXT_TOKENS
    ) -> str:
        """Shrink the continuity block if we are running out of tokens.

        Args:
            base_input_tokens: Tokens already used by base prompt + current chunk
            max_input_tokens: Maximum allowed input tokens

        Returns:
            Fitted continuity block or empty string if budget exceeded
        """
        continuity_block = self.get_continuity_block()
        if not continuity_block:
            return ""

        return fit_continuity_to_budget(continuity_block, base_input_tokens, max_input_tokens)

    def reset(self) -> None:
        """Wipe the slate clean."""
        self.prev_input_text = ""
        self.prev_output_text = ""
        self.prev_input_tokens = []
        self.prev_output_tokens = []


def extract_continuity_examples(prev_text: str, prev_tokens: list[int], sample_size: int) -> str:
    """Grab the last N tokens of text to show the model what happened recently.

    Args:
        prev_text: Previous chunk text (fallback if decode fails)
        prev_tokens: Previous token list
        sample_size: Number of tokens to extract

    Returns:
        Text string for continuity example
    """
    if not prev_tokens or sample_size <= 0:
        return ""

    # Extract last N tokens
    example_tokens = prev_tokens[-sample_size:]

    # Try to decode tokens back to text
    decoded_text = decode_tokens_safely(example_tokens)

    # If decode failed or returned fallback, use character-based approximation
    if decoded_text.startswith("[") and decoded_text.endswith("_FALLBACK]"):
        # Rough character approximation: assume ~4 chars per token average
        approx_chars = sample_size * 4
        decoded_text = prev_text[-approx_chars:] if len(prev_text) > approx_chars else prev_text
        logger.debug(f"Using character approximation for continuity: {len(decoded_text)} chars")

    return decoded_text


def build_continuity_block(input_example: str, output_example: str) -> str:
    """Format the continuity block using our hardcoded template.

    Args:
        input_example: Previous input text excerpt
        output_example: Previous output text excerpt

    Returns:
        Formatted continuity block
    """
    return CONTINUITY_TEMPLATE.format(input_example=input_example, output_example=output_example)


def fit_continuity_to_budget(
    continuity_block: str,
    base_input_tokens: int,
    max_input_tokens: int = MAX_CONTEXT_TOKENS,
) -> str:
    """Cut down the continuity text until it fits in the remaining token allowance.

    Args:
        continuity_block: Full continuity block text
        base_input_tokens: Tokens used by base prompt + current chunk
        max_input_tokens: Maximum allowed input tokens

    Returns:
        Truncated continuity block or empty string if budget exceeded
    """
    continuity_tokens = len(encode_text(continuity_block))
    total_tokens = base_input_tokens + continuity_tokens

    if total_tokens <= max_input_tokens:
        return continuity_block

    available_tokens = max_input_tokens - base_input_tokens

    if available_tokens <= 0:
        logger.debug("No token budget available for continuity, dropping entirely")
        return ""

    logger.debug(f"Continuity budget: {available_tokens} tokens (need {continuity_tokens})")

    # Iteratively halve the text until it fits within budget or becomes too small
    truncated_text = continuity_block
    min_useful_tokens = 20
    while len(truncated_text) > 0:
        truncated_text = truncated_text[: len(truncated_text) // 2]
        truncated_tokens = len(encode_text(truncated_text))
        if truncated_tokens < min_useful_tokens:
            logger.debug("Continuity too small to be useful after truncation, dropping")
            return ""
        if base_input_tokens + truncated_tokens <= max_input_tokens:
            logger.info(
                f"Continuity truncated from {continuity_tokens} to {truncated_tokens} tokens"
            )
            return truncated_text

    logger.debug("Continuity could not fit in budget, dropping")
    return ""


def calculate_continuity_budget(
    chunk_tokens: int,
    base_prompt_tokens: int,
    sample_size: int,
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
) -> int:
    """Figure out how many tokens we can spend on context.

    Args:
        chunk_tokens: Tokens in current chunk
        base_prompt_tokens: Tokens in base prompt
        sample_size: Desired sample size
        max_context_tokens: Maximum context window

    Returns:
        Available tokens for continuity
    """
    used_tokens = chunk_tokens + base_prompt_tokens
    available = max_context_tokens - used_tokens

    # Reserve some buffer for safety
    buffer = 1000
    available -= buffer

    if available <= 0:
        logger.debug("No token budget available for continuity")
        return 0

    # Don't use more than requested sample_size * 2 (input + output)
    max_continuity = sample_size * 2
    return min(available, max_continuity)
