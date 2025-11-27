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
    "CHARS_PER_TOKEN_FALLBACK",
    "CODE_BOUNDARY_PATTERNS",
    "COMPILED_BOUNDARY_PATTERNS",
    "DEFAULT_CHUNK_SIZE",
    "MAX_CONTEXT_TOKENS",
    "MAX_OUTPUT_TOKENS",
    "METADATA_SCHEMA",
    "MIN_COMPLETION_TOKENS",
    "REASONING_COMPLETION_RATIO",
    "REQUIRED_METADATA_FIELDS",
    "VALID_DATA_FORMATS",
    "APIError",
    "CerebrateError",
    "ChunkingError",
    "ConfigurationError",
    "FileError",
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

# Character-based fallback approximation
CHARS_PER_TOKEN_FALLBACK = 4  # Approximate 4 chars per token

# Note: Rate limiting, model defaults, and logging configuration are now
# loaded from settings (default_config.toml). The following are kept for
# backward compatibility but settings.py should be preferred.
#
# To configure models, edit:
# - Built-in: src/cerebrate_file/default_config.toml
# - User: ~/.config/cerebrate-file/config.toml
# - Project: .cerebrate-file.toml

# Valid data formats for chunking
VALID_DATA_FORMATS: set[str] = {"text", "semantic", "markdown", "code"}

# Continuity template for chunk processing
CONTINUITY_TEMPLATE = """
---
### Previous Input:
{input_example}

---
### Previous Output:
{output_example}

---

Based on the preceding context, please process the current input text, maintaining logical and stylistic continuity.
"""


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
