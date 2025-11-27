#!/usr/bin/env python3
# this_file: src/cerebrate_file/__init__.py

"""cerebrate_file: Process large documents through LLM inference with smart chunking.

This package provides tools for processing large documents by chunking them
into manageable pieces, processing each chunk through LLM models,
and stitching the results back together with context preservation.

Main Components:
- CLI interface for command-line usage
- Chunking strategies for different content types
- Continuity management for coherent results
- Rate limiting and error handling with fallback support
- Frontmatter metadata processing
- Configurable model settings (TOML-based)

Configuration:
- Built-in: default_config.toml (package defaults)
- User: ~/.config/cerebrate-file/config.toml
- Project: .cerebrate-file.toml
"""

try:
    from .__version__ import __version__
except ImportError:
    __version__ = "unknown"

# Main public interface
from .cli import run
from .models import Chunk, ProcessingState, RateLimitStatus
from .settings import (
    InferenceConfig,
    ModelConfig,
    RateLimitConfig,
    Settings,
    get_settings,
    reload_settings,
)

__all__ = [
    "Chunk",
    "InferenceConfig",
    "ModelConfig",
    "ProcessingState",
    "RateLimitConfig",
    "RateLimitStatus",
    "Settings",
    "__version__",
    "get_settings",
    "reload_settings",
    "run",
]
