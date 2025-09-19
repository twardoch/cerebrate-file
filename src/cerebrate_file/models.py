#!/usr/bin/env python3
# this_file: src/cerebrate_file/models.py

"""Data models for cerebrate_file package.

This module contains all dataclasses and data structures used throughout
the cerebrate_file package for representing chunks, processing state,
and API responses.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

__all__ = [
    "Chunk",
    "RateLimitStatus",
    "ProcessingState",
    "ProcessingResult",
    "ChunkingConfig",
    "APIConfig",
]


@dataclass
class Chunk:
    """Represents a text chunk with its token count.

    A chunk is a portion of the original document that fits within
    the model's context window and can be processed independently.

    Attributes:
        text: The actual text content of the chunk
        token_count: Number of tokens in this chunk
        metadata: Optional metadata associated with the chunk
    """

    text: str
    token_count: int
    metadata: Optional[Dict[str, Any]] = None

    def __len__(self) -> int:
        """Return the token count for convenient length checking."""
        return self.token_count

    def is_empty(self) -> bool:
        """Check if the chunk is empty or only whitespace."""
        return not self.text.strip()


@dataclass
class RateLimitStatus:
    """Rate limit information from API response headers.

    Tracks rate limiting information to ensure we don't exceed
    API quotas and implement appropriate backoff strategies.

    Attributes:
        requests_remaining: Number of requests remaining for the day
        tokens_remaining: Number of tokens remaining for the minute
        reset_time: When the token limit resets
        headers_parsed: Whether we successfully parsed rate limit headers
        tokens_limit: Maximum tokens per minute
        requests_limit: Maximum requests per day
        requests_reset_time: When the request limit resets
        last_updated: When this status was last updated
    """

    requests_remaining: int = 0
    tokens_remaining: int = 0
    reset_time: Optional[datetime] = None
    headers_parsed: bool = False  # Track if we successfully parsed headers

    # Additional tracking for rate management
    tokens_limit: int = 0  # Max tokens per minute
    requests_limit: int = 0  # Max requests per day
    requests_reset_time: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Initialize default values for reset times."""
        if self.reset_time is None:
            self.reset_time = datetime.now() + timedelta(minutes=1)
        if self.requests_reset_time is None:
            self.requests_reset_time = datetime.now() + timedelta(days=1)
        if self.last_updated is None:
            self.last_updated = datetime.now()

    def is_tokens_exhausted(self, next_request_tokens: int = 0) -> bool:
        """Check if we're out of tokens for the current minute."""
        return self.tokens_remaining < next_request_tokens

    def is_requests_exhausted(self) -> bool:
        """Check if we're out of requests for the current day."""
        return self.requests_remaining <= 0

    def time_until_token_reset(self) -> float:
        """Get seconds until token limit resets."""
        if self.reset_time is None:
            return 0.0
        delta = self.reset_time - datetime.now()
        return max(0.0, delta.total_seconds())

    def time_until_request_reset(self) -> float:
        """Get seconds until request limit resets."""
        if self.requests_reset_time is None:
            return 0.0
        delta = self.requests_reset_time - datetime.now()
        return max(0.0, delta.total_seconds())


@dataclass
class ProcessingState:
    """Tracks state across chunk processing.

    Maintains continuity information and processing statistics
    across multiple chunks in a single document.

    Attributes:
        prev_input_tokens: Token IDs from the previous input chunk
        prev_output_tokens: Token IDs from the previous output
        prev_input_text: Text from the previous input chunk
        prev_output_text: Text from the previous output
        total_input_tokens: Total tokens processed so far
        total_output_tokens: Total tokens generated so far
        chunks_processed: Number of chunks processed so far
        processing_time: Total processing time in seconds
        last_rate_status: Last rate limit status from API response
    """

    prev_input_tokens: List[int] = field(default_factory=list)
    prev_output_tokens: List[int] = field(default_factory=list)
    prev_input_text: str = ""
    prev_output_text: str = ""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    chunks_processed: int = 0
    processing_time: float = 0.0
    last_rate_status: Optional["RateLimitStatus"] = None

    def update_from_chunk(
        self,
        input_text: str,
        input_tokens: List[int],
        output_text: str,
        output_tokens: List[int],
        total_input_tokens: int,
    ) -> None:
        """Update state after processing a chunk."""
        self.prev_input_text = input_text
        self.prev_input_tokens = input_tokens
        self.prev_output_text = output_text
        self.prev_output_tokens = output_tokens
        self.total_input_tokens += total_input_tokens
        self.total_output_tokens += len(output_tokens)
        self.chunks_processed += 1

    def get_average_input_tokens(self) -> float:
        """Get average input tokens per chunk."""
        if self.chunks_processed == 0:
            return 0.0
        return self.total_input_tokens / self.chunks_processed

    def get_average_output_tokens(self) -> float:
        """Get average output tokens per chunk."""
        if self.chunks_processed == 0:
            return 0.0
        return self.total_output_tokens / self.chunks_processed

    def has_previous_context(self) -> bool:
        """Check if we have previous context for continuity."""
        return bool(self.prev_input_tokens and self.prev_output_tokens)


@dataclass
class ProcessingResult:
    """Result of processing a document.

    Contains the final output and processing statistics.

    Attributes:
        output_text: The final processed text
        chunks_processed: Number of chunks that were processed
        total_input_tokens: Total input tokens consumed
        total_output_tokens: Total output tokens generated
        processing_time: Time taken for processing in seconds
        errors: Any errors encountered during processing
    """

    output_text: str
    chunks_processed: int
    total_input_tokens: int
    total_output_tokens: int
    processing_time: float
    errors: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)

    def has_errors(self) -> bool:
        """Check if there were any errors."""
        return bool(self.errors)

    def get_tokens_per_second(self) -> float:
        """Calculate processing rate in tokens per second."""
        if self.processing_time <= 0:
            return 0.0
        return self.total_input_tokens / self.processing_time


@dataclass
class ChunkingConfig:
    """Configuration for chunking strategies.

    Attributes:
        chunk_size: Maximum tokens per chunk
        data_format: Chunking strategy to use
        sample_size: Size of continuity examples in tokens
    """

    chunk_size: int
    data_format: str
    sample_size: int

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.sample_size < 0:
            raise ValueError("sample_size must be non-negative")


@dataclass
class APIConfig:
    """Configuration for API calls.

    Attributes:
        model: Model name to use
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        max_tokens_ratio: Completion budget as percentage of chunk size
    """

    model: str
    temperature: float
    top_p: float
    max_tokens_ratio: int

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")
        if not (0.0 <= self.top_p <= 1.0):
            raise ValueError("top_p must be between 0.0 and 1.0")
        if not (1 <= self.max_tokens_ratio <= 100):
            raise ValueError("max_tokens_ratio must be between 1 and 100")