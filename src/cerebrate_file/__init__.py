#!/usr/bin/env python3
# this_file: src/cerebrate_file/__init__.py

"""cerebrate_file: Process large documents through Cerebras AI models with smart chunking.

This package provides tools for processing large documents by chunking them
into manageable pieces, processing each chunk through Cerebras AI models,
and stitching the results back together with context preservation.

Main Components:
- CLI interface for command-line usage
- Chunking strategies for different content types
- Continuity management for coherent results
- Rate limiting and error handling
- Frontmatter metadata processing
"""

try:
    from .__version__ import __version__
except ImportError:
    __version__ = "unknown"

# Main public interface
from .cli import run
from .models import Chunk, ProcessingState, RateLimitStatus

__all__ = [
    "Chunk",
    "ProcessingState",
    "RateLimitStatus",
    "__version__",
    "run",
]
