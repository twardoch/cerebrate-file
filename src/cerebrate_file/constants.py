#!/usr/bin/env python3
# this_file: src/cerebrate_file/constants.py

"""Constants and shared configuration for cerebrate_file package.

This module contains all constants, schemas, and configuration values
used throughout the cerebrate_file package for processing large documents
with Cerebras AI models.
"""

import re
from re import Pattern
from typing import Any

__all__ = [
    "CODE_BOUNDARY_PATTERNS",
    "COMPILED_BOUNDARY_PATTERNS",
    "DEFAULT_CHUNK_SIZE",
    "MAX_CONTEXT_TOKENS",
    "MAX_OUTPUT_TOKENS",
    "MIN_COMPLETION_TOKENS",
    "REASONING_COMPLETION_RATIO",
    "METADATA_SCHEMA",
    "REQUIRED_METADATA_FIELDS",
    "APIError",
    "CerebrateError",
    "ChunkingError",
    "TokenizationError",
    "ValidationError",
]

# Model limits - actual context window is 131K tokens, max output is 40K tokens
MAX_CONTEXT_TOKENS = 131000
MAX_OUTPUT_TOKENS = 40000
DEFAULT_CHUNK_SIZE = 32000  # Conservative chunk size for better processing
MIN_COMPLETION_TOKENS = 4096  # Minimum completion budget per chunk to satisfy reasoning models
REASONING_COMPLETION_RATIO = 450  # Allocate at least 4.5x the chunk input tokens for completions

# Required metadata fields for --explain mode
REQUIRED_METADATA_FIELDS: set[str] = {"title", "author", "id", "type", "date"}

# JSON schema for metadata structured output
METADATA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "author": {"type": "string"},
        "id": {"type": "string"},
        "type": {"type": "string"},
        "date": {"type": "string"},
    },
    "required": ["title", "author", "id", "type", "date"],
    "additionalProperties": False,
}

# Code boundary patterns for intelligent chunking
# These patterns identify good split points in code
CODE_BOUNDARY_PATTERNS: list[str] = [
    # Function/method definitions
    r"^(?:def |function |func |fn |public |private |protected |static ).*\{?\s*$",
    # Class definitions
    r"^(?:class |struct |interface |enum ).*\{?\s*$",
    # Import/include statements
    r"^(?:import |from .* import|include |require |using ).*$",
    # Namespace/module boundaries
    r"^(?:namespace |module |package ).*\{?\s*$",
    # Comment blocks as natural boundaries
    r"^(?:/\*\*|\*/|###+|///).*$",
    # Empty lines between logical blocks
    r"^\s*$",
]

# Compiled patterns for efficiency
COMPILED_BOUNDARY_PATTERNS: list[Pattern[str]] = [
    re.compile(pattern, re.MULTILINE) for pattern in CODE_BOUNDARY_PATTERNS
]

# Rate limiting configuration
TOKENS_SAFETY_MARGIN = 50000  # Reserve 50k tokens for other instances
REQUESTS_SAFETY_MARGIN = 100  # Reserve 100 requests for other instances

# Character-based fallback approximation
CHARS_PER_TOKEN_FALLBACK = 4  # Approximate 4 chars per token

# Logging configuration
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# API configuration
DEFAULT_MODEL = "zai-glm-4.6"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_P = 0.8
DEFAULT_MAX_TOKENS_RATIO = 100
DEFAULT_SAMPLE_SIZE = 200

# Valid data formats for chunking
VALID_DATA_FORMATS: set[str] = {"text", "semantic", "markdown", "code"}

# Continuity template for chunk processing
CONTINUITY_TEMPLATE = """Our current input text chunk is the immediate continuation of this input text chunk:

<previous_input>
(...){input_example}
</previous_input>

and the previous input chunk has been processed like so:

<previous_output>
(...){output_example}
</previous_output>

Please process our current input text analogically, and maintain logical and stylistic continuity of the text."""


# Exception Classes
class CerebrateError(Exception):
    """Base exception class for cerebrate_file package."""


class TokenizationError(CerebrateError):
    """Exception raised when tokenization fails."""


class ChunkingError(CerebrateError):
    """Exception raised when chunking fails."""


class APIError(CerebrateError):
    """Exception raised when API calls fail."""


class ValidationError(CerebrateError):
    """Exception raised when input validation fails."""


class ConfigurationError(CerebrateError):
    """Exception raised when configuration is invalid."""


class FileError(CerebrateError):
    """Exception raised when file operations fail."""
