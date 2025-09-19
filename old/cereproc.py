#!/usr/bin/env -S uv run -s
# /// script
# dependencies = [
#     "fire",
#     "loguru",
#     "python-dotenv",
#     "tenacity",
#     "cerebras-cloud-sdk",
#     "semantic-text-splitter",
#     "qwen-tokenizer",
#     "tqdm",
#     "python-frontmatter"
# ]
# ///
# this_file: cereproc.py

"""
cereproc.py - Process large documents by chunking for Cerebras qwen-3-coder-480b

Intelligently splits large text into model-sized chunks, processes each through
Cerebras API while maintaining continuity, and concatenates results.
"""

import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import fire
import frontmatter
import json
from dotenv import load_dotenv
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from tqdm import tqdm

# Import order matches dependency priority
try:
    from qwen_tokenizer import get_tokenizer

    # Initialize tokenizer for qwen models - using qwen-max as it should be compatible
    qwen_tokenizer = get_tokenizer("qwen-max")
except ImportError:
    logger.error("qwen-tokenizer not available. Install with: uv add qwen-tokenizer")
    sys.exit(1)
except Exception as e:
    logger.error(f"Failed to initialize qwen tokenizer: {e}")
    logger.info("Falling back to character-based approximation")
    qwen_tokenizer = None

try:
    from semantic_text_splitter import TextSplitter, MarkdownSplitter
except ImportError:
    logger.error(
        "semantic-text-splitter not available. Install with: uv add semantic-text-splitter"
    )
    sys.exit(1)

try:
    from cerebras.cloud.sdk import Cerebras
    import cerebras.cloud.sdk
except ImportError:
    logger.error(
        "cerebras-cloud-sdk not available. Install with: uv add cerebras-cloud-sdk"
    )
    sys.exit(1)

# Model limits - actual context window is 131K tokens, max output is 40K tokens
MAX_CONTEXT_TOKENS = 131000
MAX_OUTPUT_TOKENS = 40000
DEFAULT_CHUNK_SIZE = 32000  # Conservative chunk size for better processing

# Required metadata fields for --explain mode
REQUIRED_METADATA_FIELDS = {"title", "author", "id", "type", "date"}

# JSON schema for metadata structured output
METADATA_SCHEMA = {
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


@dataclass
class Chunk:
    """Represents a text chunk with its token count."""

    text: str
    token_count: int
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RateLimitStatus:
    """Rate limit information from API response headers."""

    requests_remaining: int = 0
    tokens_remaining: int = 0
    reset_time: Optional[datetime] = None
    headers_parsed: bool = False  # Track if we successfully parsed headers

    # Additional tracking for rate management
    tokens_limit: int = 0  # Max tokens per minute
    requests_limit: int = 0  # Max requests per day
    requests_reset_time: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def __post_init__(self):
        if self.reset_time is None:
            self.reset_time = datetime.now() + timedelta(minutes=1)
        if self.requests_reset_time is None:
            self.requests_reset_time = datetime.now() + timedelta(days=1)
        if self.last_updated is None:
            self.last_updated = datetime.now()


@dataclass
class ProcessingState:
    """Tracks state across chunk processing."""

    prev_input_tokens: List[int] = field(default_factory=list)
    prev_output_tokens: List[int] = field(default_factory=list)
    prev_input_text: str = ""
    prev_output_text: str = ""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    chunks_processed: int = 0


def encode_text(text: str) -> List[int]:
    """
    Encode text to tokens with fallback handling.

    Args:
        text: Text to encode

    Returns:
        List of token IDs
    """
    if qwen_tokenizer is None:
        # Character-based fallback: approximate 4 chars per token
        return list(range(len(text) // 4 + 1))

    try:
        return qwen_tokenizer.encode(text)
    except Exception as e:
        logger.warning(f"Tokenizer encode failed: {e}, using character fallback")
        return list(range(len(text) // 4 + 1))


def decode_tokens_safely(tokens: List[int]) -> str:
    """
    Decode tokens back to text with fallback handling.

    Args:
        tokens: List of token IDs

    Returns:
        Decoded text string
    """
    if qwen_tokenizer is None:
        return "[NO_TOKENIZER_FALLBACK]"

    try:
        # Check if tokenizer has decode method
        if hasattr(qwen_tokenizer, "decode"):
            return qwen_tokenizer.decode(tokens)
        else:
            # Fallback: this is a limitation we'll handle gracefully
            logger.debug("Tokenizer decode not available, using fallback")
            return "[DECODED_TOKENS_FALLBACK]"
    except Exception as e:
        logger.warning(f"Token decode failed: {e}, using fallback")
        return "[DECODE_ERROR_FALLBACK]"


def parse_frontmatter_content(content: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse frontmatter from content using python-frontmatter.

    Args:
        content: Input text content that may contain frontmatter

    Returns:
        Tuple of (metadata_dict, content_without_frontmatter)
    """
    try:
        post = frontmatter.loads(content)
        metadata = post.metadata if post.metadata else {}
        content_only = post.content if post.content else content

        logger.debug(
            f"Frontmatter parsed: {len(metadata)} metadata fields, {len(content_only)} content chars"
        )
        return metadata, content_only

    except Exception as e:
        logger.warning(f"Frontmatter parsing failed: {e}, treating as plain content")
        return {}, content


def check_metadata_completeness(metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Check if metadata contains all required fields.

    Args:
        metadata: Parsed metadata dictionary

    Returns:
        Tuple of (is_complete, missing_fields_list)
    """
    missing_fields = []
    for field in REQUIRED_METADATA_FIELDS:
        if field not in metadata or not metadata[field]:
            missing_fields.append(field)

    is_complete = len(missing_fields) == 0
    logger.debug(f"Metadata completeness: {is_complete}, missing: {missing_fields}")

    return is_complete, missing_fields


def setup_logging(verbose: bool = False) -> None:
    """Configure Loguru logging with appropriate verbosity."""
    logger.remove()  # Remove default handler

    log_level = "DEBUG" if verbose else "WARNING"
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    logger.add(sys.stderr, level=log_level, format=log_format, colorize=True)


def validate_environment() -> None:
    """Validate required environment variables and dependencies."""
    api_key = os.getenv("CEREBRAS_API_KEY")

    if not api_key:
        print("❌ Error: CEREBRAS_API_KEY environment variable not set")
        print("\n  To fix this, run one of the following:")
        print("    export CEREBRAS_API_KEY='your-api-key'  # For current session")
        print("    echo 'CEREBRAS_API_KEY=your-api-key' >> .env  # Using .env file")
        print("\n  Get your API key from: https://cloud.cerebras.ai")
        logger.error("CEREBRAS_API_KEY not set")
        sys.exit(1)

    # Check for common placeholder values
    if api_key in [
        "your-api-key",
        "YOUR_API_KEY",
        "test-key",
        "api-key",
        "<your-api-key>",
    ]:
        print("❌ Error: API key appears to be a placeholder")
        print("   Please replace it with your actual Cerebras API key.")
        print("   Get your API key from: https://cloud.cerebras.ai")
        logger.error(f"Placeholder API key detected")
        sys.exit(1)

    # More thorough API key validation
    if not api_key.startswith("csk-"):
        logger.warning("API key doesn't start with 'csk-', this may be incorrect")

    # Check API key length (typical Cerebras keys are ~56 characters)
    if len(api_key) < 40:
        logger.warning(f"API key seems short: {len(api_key)} characters (expected ~56)")


def validate_inputs(
    input_data: str,
    chunk_size: int,
    sample_size: int,
    max_tokens_ratio: int,
    data_format: str = "text",
) -> None:
    """Validate CLI input parameters with user-friendly error messages."""
    # Check file existence with helpful error message
    input_path = Path(input_data)
    if not input_path.exists():
        print(f"❌ Error: Input file not found: '{input_data}'")
        print(f"   Please check the file path and ensure the file exists.")
        logger.error(f"Input file not found: {input_data}")
        sys.exit(1)

    if not input_path.is_file():
        print(f"❌ Error: Path is not a file: '{input_data}'")
        print(f"   Expected a file, but found a directory or other type.")
        logger.error(f"Input path is not a file: {input_data}")
        sys.exit(1)

    # Check if file is readable
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            f.read(1)  # Try reading one character
    except PermissionError:
        print(f"❌ Error: Permission denied reading file: '{input_data}'")
        print(f"   Please check file permissions.")
        logger.error(f"Permission denied reading file: {input_data}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: Cannot read file: '{input_data}'")
        print(f"   {str(e)}")
        logger.error(f"Cannot read file {input_data}: {e}")
        sys.exit(1)

    # Validate chunk_size with clear limits
    if chunk_size <= 0:
        print(f"❌ Error: chunk_size must be positive, got: {chunk_size}")
        print(f"   Use a value between 1 and {MAX_CONTEXT_TOKENS:,} tokens.")
        logger.error(f"Invalid chunk_size: {chunk_size}")
        sys.exit(1)

    if chunk_size > MAX_CONTEXT_TOKENS:
        print(f"❌ Error: chunk_size exceeds model's context limit")
        print(f"   Maximum allowed: {MAX_CONTEXT_TOKENS:,} tokens")
        print(f"   You provided: {chunk_size:,} tokens")
        print(f"   Recommended: 32000 tokens for optimal processing")
        logger.error(f"chunk_size exceeds limit: {chunk_size} > {MAX_CONTEXT_TOKENS}")
        sys.exit(1)

    # Validate sample_size
    if sample_size < 0:
        print(f"❌ Error: sample_size must be non-negative, got: {sample_size}")
        print(f"   Use 0 to disable continuity, or a positive value for context size.")
        logger.error(f"Invalid sample_size: {sample_size}")
        sys.exit(1)

    if sample_size > chunk_size // 4:
        print(
            f"⚠️  Warning: sample_size ({sample_size}) is large relative to chunk_size ({chunk_size})"
        )
        print(
            f"   This may reduce effective chunk size. Consider using a smaller sample_size."
        )
        logger.warning(
            f"Large sample_size relative to chunk_size: {sample_size}/{chunk_size}"
        )

    # Validate max_tokens_ratio
    if max_tokens_ratio < 1 or max_tokens_ratio > 100:
        print(
            f"❌ Error: max_tokens_ratio must be between 1 and 100, got: {max_tokens_ratio}"
        )
        print(
            f"   This value represents the completion budget as a percentage of chunk size."
        )
        print(
            f"   Use 100 for equal input/output size, or lower for shorter responses."
        )
        logger.error(f"Invalid max_tokens_ratio: {max_tokens_ratio}")
        sys.exit(1)

    # Validate data_format
    valid_formats = ["text", "semantic", "markdown", "code"]
    if data_format not in valid_formats:
        print(f"❌ Error: Invalid data_format: '{data_format}'")
        print(f"   Valid options are: {', '.join(valid_formats)}")
        print(f"   • text: Line-based chunking (default)")
        print(f"   • semantic: Smart paragraph/sentence boundaries")
        print(f"   • markdown: Respect Markdown structure")
        print(f"   • code: Programming language-aware chunking")
        logger.error(f"Invalid data_format: {data_format}")
        sys.exit(1)

    logger.debug(f"Input validation passed for: {input_data}")


def read_file_safely(file_path: str) -> str:
    """Read file content with error handling."""
    try:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        logger.debug(f"Read {len(content)} characters from {file_path}")
        return content
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        sys.exit(1)


def build_base_prompt(
    file_prompt: Optional[str], text_prompt: Optional[str]
) -> Tuple[str, int]:
    """
    Assemble base prompt from file and text components.

    Returns:
        Tuple of (prompt_text, token_count)
    """
    base_prompt = ""

    # Read file prompt if provided
    if file_prompt:
        if not Path(file_prompt).exists():
            logger.error(f"Prompt file not found: {file_prompt}")
            sys.exit(1)
        base_prompt += read_file_safely(file_prompt)
        logger.debug(f"Loaded file prompt from: {file_prompt}")

    # Add separator (always two newlines per spec)
    base_prompt += "\n\n"

    # Append text prompt if provided
    if text_prompt:
        base_prompt += text_prompt
        logger.debug(f"Added text prompt: {text_prompt[:50]}...")

    # Calculate token count
    token_count = len(encode_text(base_prompt))
    logger.info(f"Base prompt assembled: {token_count} tokens")

    return base_prompt, token_count


def chunk_text_mode(content: str, chunk_size: int) -> List[Chunk]:
    """
    Line-based greedy accumulation respecting token limits.

    Args:
        content: Input text content
        chunk_size: Maximum tokens per chunk

    Returns:
        List of Chunk objects with text and token counts
    """
    chunks = []
    lines = content.splitlines(keepends=True)

    current_chunk = ""
    current_tokens = 0

    for line in lines:
        line_tokens = len(encode_text(line))

        # If adding this line would exceed chunk size and we have content, finalize chunk
        if current_tokens + line_tokens > chunk_size and current_chunk:
            chunks.append(Chunk(current_chunk, current_tokens))
            current_chunk = line
            current_tokens = line_tokens
        else:
            current_chunk += line
            current_tokens += line_tokens

        # Handle overlong single lines
        if line_tokens > chunk_size:
            logger.warning(
                f"Single line exceeds chunk_size ({line_tokens} > {chunk_size}), "
                f"processing as individual chunk"
            )

    # Add final chunk if any content remains
    if current_chunk:
        chunks.append(Chunk(current_chunk, current_tokens))

    logger.info(f"Text mode chunking: {len(chunks)} chunks created")
    return chunks


def chunk_semantic_mode(content: str, chunk_size: int) -> List[Chunk]:
    """
    Use semantic-text-splitter with token callback.

    Args:
        content: Input text content
        chunk_size: Maximum tokens per chunk

    Returns:
        List of Chunk objects
    """
    try:
        # Use character-based approximation for now to avoid tokenizer recursion
        splitter = TextSplitter(chunk_size * 4)  # Approximate: 4 chars per token
        chunk_texts = splitter.chunks(content)

        chunks = [Chunk(text, len(encode_text(text))) for text in chunk_texts]

        logger.info(f"Semantic mode chunking: {len(chunks)} chunks created")
        return chunks

    except Exception as e:
        logger.warning(f"Semantic chunking failed: {e}, falling back to text mode")
        return chunk_text_mode(content, chunk_size)


def chunk_markdown_mode(content: str, chunk_size: int) -> List[Chunk]:
    """
    Use MarkdownSplitter with token callback.

    Args:
        content: Input text content
        chunk_size: Maximum tokens per chunk

    Returns:
        List of Chunk objects
    """
    try:
        # Use character-based approximation for now to avoid tokenizer recursion
        splitter = MarkdownSplitter(chunk_size * 4)  # Approximate: 4 chars per token
        chunk_texts = splitter.chunks(content)

        chunks = [Chunk(text, len(encode_text(text))) for text in chunk_texts]

        logger.info(f"Markdown mode chunking: {len(chunks)} chunks created")
        return chunks

    except Exception as e:
        logger.warning(f"Markdown chunking failed: {e}, falling back to text mode")
        return chunk_text_mode(content, chunk_size)


def chunk_code_mode(content: str, chunk_size: int) -> List[Chunk]:
    """
    Code-aware chunking that respects code structure boundaries.

    Args:
        content: Input text content
        chunk_size: Maximum tokens per chunk

    Returns:
        List of Chunk objects
    """
    import re

    logger.debug("Using code-aware chunking strategy")

    # Define patterns for code structure boundaries (Python, JS, Java, C++, etc.)
    # These patterns identify good split points in code
    boundary_patterns = [
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

    # Compile patterns for efficiency
    compiled_patterns = [
        re.compile(pattern, re.MULTILINE) for pattern in boundary_patterns
    ]

    chunks = []
    lines = content.splitlines(keepends=True)

    # Track current chunk
    current_chunk = []
    current_tokens = 0

    # Track if we're inside a multi-line structure
    brace_depth = 0
    paren_depth = 0
    in_string = False
    string_delimiter = None

    def is_good_split_point(line_idx: int, line: str) -> bool:
        """Determine if this is a good place to split chunks."""
        # Don't split if we're inside nested structures
        if brace_depth > 0 or paren_depth > 0 or in_string:
            return False

        # Check if line matches any boundary pattern
        for pattern in compiled_patterns:
            if pattern.match(line):
                return True

        # Also good to split before function/class definitions
        if line_idx > 0:
            stripped = line.strip()
            if any(
                stripped.startswith(kw)
                for kw in ["def ", "class ", "function ", "public ", "private "]
            ):
                return True

        return False

    for idx, line in enumerate(lines):
        # Track structure depth for better splitting decisions
        for char in line:
            if not in_string:
                if char in ['"', "'"]:
                    if not (idx > 0 and line[idx - 1] == "\\"):
                        in_string = True
                        string_delimiter = char
                elif char == "{":
                    brace_depth += 1
                elif char == "}":
                    brace_depth = max(0, brace_depth - 1)
                elif char == "(":
                    paren_depth += 1
                elif char == ")":
                    paren_depth = max(0, paren_depth - 1)
            else:
                if char == string_delimiter and not (idx > 0 and line[idx - 1] == "\\"):
                    in_string = False
                    string_delimiter = None

        line_tokens = len(encode_text(line))

        # Check if adding this line would exceed chunk size
        if current_tokens + line_tokens > chunk_size and current_chunk:
            # Look for a good split point
            if is_good_split_point(idx, line):
                # Create chunk at this boundary
                chunks.append(Chunk("".join(current_chunk), current_tokens))
                current_chunk = [line]
                current_tokens = line_tokens
            else:
                # If we must split but not at a good point, try to find the last good point
                if len(current_chunk) > 10:  # Only look back if we have enough lines
                    # Find the last good split point in current chunk
                    for back_idx in range(
                        len(current_chunk) - 1, max(0, len(current_chunk) - 20), -1
                    ):
                        back_line = current_chunk[back_idx]
                        if any(
                            pattern.match(back_line) for pattern in compiled_patterns
                        ):
                            # Split at this earlier good point
                            chunk_before = current_chunk[:back_idx]
                            chunk_after = current_chunk[back_idx:]

                            if chunk_before:
                                before_tokens = sum(
                                    len(encode_text(l)) for l in chunk_before
                                )
                                chunks.append(
                                    Chunk("".join(chunk_before), before_tokens)
                                )

                            current_chunk = chunk_after + [line]
                            current_tokens = sum(
                                len(encode_text(l)) for l in current_chunk
                            )
                            break
                    else:
                        # No good split found, force split here
                        chunks.append(Chunk("".join(current_chunk), current_tokens))
                        current_chunk = [line]
                        current_tokens = line_tokens
                else:
                    # Force split for small chunks
                    chunks.append(Chunk("".join(current_chunk), current_tokens))
                    current_chunk = [line]
                    current_tokens = line_tokens
        else:
            current_chunk.append(line)
            current_tokens += line_tokens

        # Handle overlong single lines (shouldn't happen in well-formatted code)
        if line_tokens > chunk_size:
            logger.warning(
                f"Single line exceeds chunk_size ({line_tokens} > {chunk_size}), "
                f"processing as individual chunk"
            )
            if current_chunk and current_chunk[-1] == line:
                current_chunk.pop()  # Remove the line we just added
            if current_chunk:
                chunks.append(
                    Chunk("".join(current_chunk), current_tokens - line_tokens)
                )
                current_chunk = []
                current_tokens = 0
            chunks.append(Chunk(line, line_tokens))

    # Add any remaining content
    if current_chunk:
        chunks.append(Chunk("".join(current_chunk), current_tokens))

    logger.info(f"Code mode chunking: {len(chunks)} chunks created")
    return chunks


def extract_continuity_examples(
    prev_text: str, prev_tokens: List[int], sample_size: int
) -> str:
    """
    Extract last N tokens from previous text as continuity example.

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
        decoded_text = (
            prev_text[-approx_chars:] if len(prev_text) > approx_chars else prev_text
        )
        logger.debug(
            f"Using character approximation for continuity: {len(decoded_text)} chars"
        )

    return decoded_text


def build_continuity_block(input_example: str, output_example: str) -> str:
    """
    Build continuity block using exact template from spec.

    Args:
        input_example: Previous input text excerpt
        output_example: Previous output text excerpt

    Returns:
        Formatted continuity block
    """
    template = """Our current input text chunk is the immediate continuation of this input text chunk:

<previous_input>
(...){input_example}
</previous_input>

and the previous input chunk has been processed like so:

<previous_output>
(...){output_example}
</previous_output>

Please process our current input text analogically, and maintain logical and stylistic continuity of the text."""

    return template.format(input_example=input_example, output_example=output_example)


def fit_continuity_to_budget(
    continuity_block: str,
    base_input_tokens: int,
    max_input_tokens: int = MAX_CONTEXT_TOKENS,
) -> str:
    """
    Truncate continuity examples to fit within token budget.

    Args:
        continuity_block: Full continuity block text
        base_input_tokens: Tokens used by base prompt + current chunk
        max_input_tokens: Maximum allowed input tokens (default: 131K model context window)

    Returns:
        Truncated continuity block or empty string if budget exceeded
    """
    continuity_tokens = len(encode_text(continuity_block))
    total_tokens = base_input_tokens + continuity_tokens

    if total_tokens <= max_input_tokens:
        return continuity_block

    available_tokens = max_input_tokens - base_input_tokens

    if available_tokens <= 0:
        logger.warning("No token budget available for continuity, dropping entirely")
        return ""

    logger.debug(
        f"Continuity budget: {available_tokens} tokens (need {continuity_tokens})"
    )

    # Simple truncation: reduce both examples proportionally
    # This is a simplified approach - we could be more sophisticated
    reduction_factor = (
        available_tokens / continuity_tokens * 0.9
    )  # 90% to leave some buffer

    # Extract examples from continuity block and reduce them
    # For now, simple truncation of the whole block
    truncated_text = continuity_block[: int(len(continuity_block) * reduction_factor)]

    # Ensure we're still within budget
    truncated_tokens = len(encode_text(truncated_text))
    if base_input_tokens + truncated_tokens > max_input_tokens:
        logger.warning("Continuity still too large after truncation, dropping entirely")
        return ""

    logger.info(
        f"Continuity truncated from {continuity_tokens} to {truncated_tokens} tokens"
    )
    return truncated_text


def create_chunks(content: str, data_format: str, chunk_size: int) -> List[Chunk]:
    """
    Create chunks using the specified strategy.

    Args:
        content: Input text content
        data_format: Chunking strategy (text|semantic|markdown|code)
        chunk_size: Maximum tokens per chunk

    Returns:
        List of Chunk objects
    """
    logger.info(f"Creating chunks using {data_format} mode, max {chunk_size} tokens")

    chunking_strategies = {
        "text": chunk_text_mode,
        "semantic": chunk_semantic_mode,
        "markdown": chunk_markdown_mode,
        "code": chunk_code_mode,
    }

    if data_format not in chunking_strategies:
        logger.error(
            f"Unknown data_format: {data_format}. Must be one of: {list(chunking_strategies.keys())}"
        )
        sys.exit(1)

    chunks = chunking_strategies[data_format](content, chunk_size)

    # Log chunking statistics
    total_tokens = sum(chunk.token_count for chunk in chunks)
    avg_tokens = total_tokens / len(chunks) if chunks else 0
    logger.info(
        f"Chunking complete: {len(chunks)} chunks, {total_tokens} total tokens, "
        f"{avg_tokens:.1f} avg tokens per chunk"
    )

    return chunks


def calculate_completion_budget(chunk_tokens: int, max_tokens_ratio: int) -> int:
    """
    Calculate max_completion_tokens for this chunk.

    Args:
        chunk_tokens: Number of tokens in the current chunk
        max_tokens_ratio: Completion budget as percentage of chunk size

    Returns:
        Maximum completion tokens (capped at 40000)
    """
    # Calculate based on ratio
    requested_tokens = (chunk_tokens * max_tokens_ratio) // 100

    # Enforce hard limit
    max_completion_tokens = min(MAX_OUTPUT_TOKENS, requested_tokens)

    logger.debug(
        f"Completion budget: {chunk_tokens} chunk tokens * {max_tokens_ratio}% = "
        f"{requested_tokens} requested, capped at {max_completion_tokens}"
    )

    return max_completion_tokens


def prepare_chunk_messages(
    base_prompt: str,
    chunk: Chunk,
    continuity_block: str,
    base_prompt_tokens: int,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, str]], int]:
    """
    Prepare chat messages for API call with token validation.

    Args:
        base_prompt: System prompt text
        chunk: Current chunk to process
        continuity_block: Continuity context (may be empty)
        base_prompt_tokens: Token count for base prompt
        metadata: Optional metadata to include as context

    Returns:
        Tuple of (messages list, total_input_tokens)
    """
    # Prepare metadata context if provided
    metadata_context = ""
    if metadata:
        # Convert any non-serializable objects to strings
        serializable_metadata = {}
        for key, value in metadata.items():
            try:
                json.dumps(value)
                serializable_metadata[key] = value
            except TypeError:
                serializable_metadata[key] = str(value)

        metadata_json = json.dumps(serializable_metadata, separators=(",", ":"))
        metadata_context = (
            f"Our current input text chunk is part of the document {metadata_json}\n\n"
        )

    # Combine user content: metadata_context + continuity + chunk
    user_content_parts = []
    if metadata_context:
        user_content_parts.append(metadata_context)
    if continuity_block:
        user_content_parts.append(continuity_block)
    user_content_parts.append(chunk.text)

    user_content = "".join(user_content_parts)

    # Calculate total input tokens
    user_tokens = len(encode_text(user_content))
    total_input_tokens = base_prompt_tokens + user_tokens

    # Validate within actual model context window (131K tokens)
    if total_input_tokens > MAX_CONTEXT_TOKENS:
        logger.error(
            f"Total input tokens ({total_input_tokens}) exceeds context window limit ({MAX_CONTEXT_TOKENS})"
        )
        raise ValueError(
            f"Input too large: {total_input_tokens} tokens > {MAX_CONTEXT_TOKENS} limit"
        )

    # Prepare messages
    messages = [
        {"role": "system", "content": base_prompt},
        {"role": "user", "content": user_content},
    ]

    logger.debug(
        f"Messages prepared: {base_prompt_tokens} system + {user_tokens} user = "
        f"{total_input_tokens} total input tokens"
    )

    return messages, total_input_tokens


def parse_rate_limit_headers(headers: Dict[str, str]) -> RateLimitStatus:
    """
    Extract rate limit info from response headers.

    Args:
        headers: HTTP response headers

    Returns:
        RateLimitStatus object
    """
    try:
        status = RateLimitStatus()
        found_any_headers = False

        # Parse limits (maximum allowed)
        if "x-ratelimit-limit-requests-day" in headers:
            status.requests_limit = int(headers["x-ratelimit-limit-requests-day"])
            found_any_headers = True

        if "x-ratelimit-limit-tokens-minute" in headers:
            status.tokens_limit = int(headers["x-ratelimit-limit-tokens-minute"])
            found_any_headers = True

        # Parse remaining requests (daily limit)
        if "x-ratelimit-remaining-requests-day" in headers:
            status.requests_remaining = int(
                headers["x-ratelimit-remaining-requests-day"]
            )
            found_any_headers = True

        # Parse remaining tokens (per-minute limit)
        if "x-ratelimit-remaining-tokens-minute" in headers:
            status.tokens_remaining = int(
                headers["x-ratelimit-remaining-tokens-minute"]
            )
            found_any_headers = True

        # Parse reset time for tokens (per-minute)
        if "x-ratelimit-reset-tokens-minute" in headers:
            reset_value = headers["x-ratelimit-reset-tokens-minute"]
            try:
                # Reset time is in seconds from now
                seconds_until_reset = float(reset_value)
                status.reset_time = datetime.now() + timedelta(
                    seconds=seconds_until_reset
                )
                found_any_headers = True
            except ValueError:
                logger.debug(f"Could not parse reset time: {reset_value}")

        # Parse reset time for requests (daily)
        if "x-ratelimit-reset-requests-day" in headers:
            reset_value = headers["x-ratelimit-reset-requests-day"]
            try:
                seconds_until_reset = float(reset_value)
                status.requests_reset_time = datetime.now() + timedelta(
                    seconds=seconds_until_reset
                )
                found_any_headers = True
            except ValueError:
                logger.debug(f"Could not parse request reset time: {reset_value}")

        # Mark that we successfully parsed headers and update timestamp
        status.headers_parsed = found_any_headers
        status.last_updated = datetime.now()

        logger.debug(
            f"Rate limit status: {status.requests_remaining}/{status.requests_limit} requests, "
            f"{status.tokens_remaining}/{status.tokens_limit} tokens remaining, parsed: {status.headers_parsed}"
        )

        return status

    except Exception as e:
        logger.warning(f"Failed to parse rate limit headers: {e}")
        return RateLimitStatus()


def calculate_backoff_delay(
    rate_status: RateLimitStatus,
    next_chunk_tokens: int,
    processing_state: Optional[object] = None,
) -> float:
    """
    Calculate optimal delay based on rate limit status with multi-instance safety.

    Args:
        rate_status: Current rate limit status
        next_chunk_tokens: Estimated tokens for next request
        processing_state: Optional processing state for rate tracking

    Returns:
        Delay in seconds
    """
    now = datetime.now()

    # Only apply rate limiting if we successfully parsed headers
    if not rate_status.headers_parsed:
        logger.debug("No rate limit headers parsed, using minimal delay")
        return 0.1

    # Define safety margins for multi-instance protection
    # Conservative margins to account for other running instances
    TOKENS_SAFETY_MARGIN = 50000  # Reserve 50k tokens for other instances
    REQUESTS_SAFETY_MARGIN = 100  # Reserve 100 requests for other instances

    # Rate-based safety thresholds
    TOKENS_PER_MINUTE_LIMIT = (
        rate_status.tokens_limit if rate_status.tokens_limit > 0 else 400000
    )
    TOKENS_PER_SECOND_LIMIT = (
        TOKENS_PER_MINUTE_LIMIT / 60.0
    )  # ~6,667 tokens/sec for 400k/min

    # Critical shortage - immediate wait until reset
    if rate_status.tokens_remaining < next_chunk_tokens:
        if rate_status.reset_time and rate_status.reset_time > now:
            delay = (rate_status.reset_time - now).total_seconds()
            logger.info(
                f"Critical token shortage ({rate_status.tokens_remaining} < {next_chunk_tokens}), "
                f"waiting {delay:.1f}s until reset"
            )
            return min(delay, 60.0)  # Cap at 60 seconds max

    # Safety margin check - entering dangerous territory
    safety_threshold = next_chunk_tokens + TOKENS_SAFETY_MARGIN
    if rate_status.tokens_remaining < safety_threshold:
        # Calculate time until we have safe tokens again
        if rate_status.reset_time and rate_status.reset_time > now:
            delay = (
                rate_status.reset_time - now
            ).total_seconds() * 0.1  # Wait 10% of time to reset
            logger.info(
                f"Approaching token safety margin ({rate_status.tokens_remaining} < {safety_threshold}), "
                f"conservative delay: {delay:.1f}s"
            )
            return min(max(delay, 1.0), 10.0)  # Between 1-10 seconds

    # Rate-based pacing - don't consume faster than sustainable rate
    if rate_status.tokens_limit > 0:
        # Calculate if we're consuming too fast
        time_since_update = (
            (now - rate_status.last_updated).total_seconds()
            if rate_status.last_updated
            else 0
        )
        if time_since_update < 1.0:  # Recent update, check consumption rate
            # Conservative pacing: don't exceed 80% of max rate
            safe_tokens_per_second = TOKENS_PER_SECOND_LIMIT * 0.8

            # If next request would exceed safe rate, add small delay
            if next_chunk_tokens > safe_tokens_per_second:
                delay = (next_chunk_tokens / safe_tokens_per_second) - 1.0
                if delay > 0:
                    logger.debug(
                        f"Rate pacing: {next_chunk_tokens} tokens > {safe_tokens_per_second:.0f} safe rate, "
                        f"delay: {delay:.2f}s"
                    )
                    return min(delay, 2.0)  # Cap at 2 seconds for rate pacing

    # Request quota safety check
    if (
        rate_status.requests_remaining >= 0
        and rate_status.requests_remaining < REQUESTS_SAFETY_MARGIN
    ):
        delay = 2.0
        logger.info(
            f"Low request quota ({rate_status.requests_remaining} < {REQUESTS_SAFETY_MARGIN}), "
            f"conservative delay: {delay}s"
        )
        return delay

    # All checks passed - minimal delay for optimal throughput
    return 0.1


def explain_metadata_with_llm(
    client: "Cerebras",
    existing_metadata: Dict[str, Any],
    first_chunk_text: str,
    model: str,
    temp: float,
    top_p: float,
) -> Dict[str, Any]:
    """
    Use structured outputs to generate missing metadata fields.

    Args:
        client: Cerebras client instance
        existing_metadata: Current metadata dictionary
        first_chunk_text: First chunk of content for context
        model: Model name to use
        temp: Model temperature
        top_p: Model top_p

    Returns:
        Dictionary with generated metadata fields
    """
    try:
        # Create explanation prompt
        existing_json = json.dumps(existing_metadata, separators=(",", ":"))

        # Truncate first chunk if too long for explanation
        max_chunk_chars = 4000  # Conservative limit for explanation context
        truncated_chunk = (
            first_chunk_text[:max_chunk_chars] + "..."
            if len(first_chunk_text) > max_chunk_chars
            else first_chunk_text
        )

        explanation_prompt = f"""<TASK>
Look at the JSON metadata and the first chunk of text below. Based on the text content, fill out any missing fields in the metadata. Return only the JSON with the missing fields filled in.

Existing metadata: {existing_json}
First chunk: {truncated_chunk}
</TASK>"""

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that analyzes documents and fills in missing metadata fields.",
            },
            {"role": "user", "content": explanation_prompt},
        ]

        logger.debug(
            f"Making metadata explanation request with {len(truncated_chunk)} chars context"
        )

        # Make structured output request
        response = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temp,
            top_p=top_p,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "metadata_schema",
                    "strict": True,
                    "schema": METADATA_SCHEMA,
                },
            },
        )

        # Parse the structured response
        response_content = response.choices[0].message.content
        generated_metadata = json.loads(response_content)

        logger.info(
            f"Metadata explanation successful: {len(generated_metadata)} fields generated"
        )
        return generated_metadata

    except Exception as e:
        logger.error(f"Metadata explanation failed: {e}")
        return {}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
def make_cerebras_request(
    client: Cerebras,
    messages: List[Dict[str, str]],
    model: str,
    max_completion_tokens: int,
    temperature: float,
    top_p: float,
) -> Tuple[str, RateLimitStatus]:
    """
    Make streaming request to Cerebras API with retry logic.

    Args:
        client: Cerebras client instance
        messages: Chat messages for the request
        model: Model name
        max_completion_tokens: Maximum tokens for completion
        temperature: Model temperature
        top_p: Model top_p

    Returns:
        Tuple of (response_text, rate_limit_status)
    """
    try:
        stream = client.chat.completions.create(
            messages=messages,
            model=model,
            stream=True,
            max_completion_tokens=max_completion_tokens,
            temperature=temperature,
            top_p=top_p,
        )

        response_text = ""
        rate_status = RateLimitStatus()

        # Extract rate limit info from stream response headers
        # Headers are available on the stream object, not individual chunks
        try:
            if hasattr(stream, "response") and hasattr(stream.response, "headers"):
                headers_dict = dict(stream.response.headers)
                rate_status = parse_rate_limit_headers(headers_dict)
                logger.debug(f"Rate limit headers parsed from stream response")
        except Exception as e:
            logger.debug(f"Could not parse rate limit headers from stream: {e}")

        for chunk in stream:
            if chunk.choices[0].delta.content:
                response_text += chunk.choices[0].delta.content

        logger.debug(f"Streaming complete: {len(response_text)} chars received")
        return response_text, rate_status

    except cerebras.cloud.sdk.RateLimitError as e:
        logger.warning(f"Rate limit hit: {e}")
        # For rate limits, we want to retry after a delay
        raise e
    except cerebras.cloud.sdk.APIStatusError as e:
        logger.error(f"API error {e.status_code}: {e.response}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in Cerebras request: {e}")
        raise e


def write_output_atomically(
    content: str, output_path: str, metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Write output using temporary file for atomicity, optionally preserving frontmatter."""
    output_path_obj = Path(output_path)
    temp_dir = output_path_obj.parent

    # If metadata is provided, wrap content with frontmatter
    if metadata:
        post = frontmatter.Post(content, **metadata)
        final_content = frontmatter.dumps(post)
    else:
        final_content = content

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=temp_dir,
            prefix=f".{output_path_obj.name}.tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(final_content)
            temp_path = temp_file.name

        # Atomic replacement
        Path(temp_path).replace(output_path_obj)
        logger.info(f"Output written atomically to: {output_path}")

    except Exception as e:
        # Clean up temp file if it exists
        if "temp_path" in locals() and Path(temp_path).exists():
            Path(temp_path).unlink()
        logger.error(f"Failed to write output to {output_path}: {e}")
        sys.exit(1)


def run(
    input_data: str,
    output_data: Optional[str] = None,
    file_prompt: Optional[str] = None,
    prompt: Optional[str] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    max_tokens_ratio: int = 100,
    data_format: str = "markdown",
    sample_size: int = 200,
    temp: float = 0.7,
    top_p: float = 0.8,
    model: str = "qwen-3-coder-480b",
    verbose: bool = False,
    explain: bool = False,
    dry_run: bool = False,
) -> None:
    """
    Process large documents by chunking for Cerebras qwen-3-coder-480b.

    Args:
        input_data: Path to input file to process
        output_data: Output file path (default: overwrite input_data)
        file_prompt: Path to file containing initial instructions
        text_prompt: Freeform instruction text to append after file_prompt
        chunk_size: Target maximum input chunk size in tokens (default: 32000)
        max_tokens_ratio: Completion budget as % of chunk size (default: 100)
        data_format: Chunking strategy - text|semantic|markdown|code (default: text)
        sample_size: Number of tokens for continuity examples (default: 200)
        temp: Model temperature (default: 0.7)
        top_p: Model top-p (default: 0.8)
        model: Model name override (default: qwen-3-coder-480b)
        verbose: Enable debug logging (default: False)
        explain: Enable metadata processing with frontmatter parsing and structured outputs (default: False)
        dry_run: Perform chunking and display results without making API calls (default: False)
    """
    # Load environment variables
    load_dotenv()

    # Setup logging first
    setup_logging(verbose)
    text_prompt = prompt

    # Always print input file path
    print(f"Processing: {input_data}")

    logger.info(f"cereproc.py starting - processing {input_data}")
    logger.debug(
        f"Parameters: chunk_size={chunk_size}, format={data_format}, "
        f"sample_size={sample_size}, model={model}"
    )

    # Validate environment and inputs
    validate_environment()
    validate_inputs(input_data, chunk_size, sample_size, max_tokens_ratio, data_format)

    # Set output path
    if output_data is None:
        output_data = input_data
        logger.info(
            f"No output_data specified, will overwrite input file: {input_data}"
        )
    else:
        logger.info(f"Output will be written to: {output_data}")

    # Build base prompt
    if verbose:
        print(f"🔧 Setting up processing...")
    base_prompt, base_prompt_tokens = build_base_prompt(file_prompt, text_prompt)
    if verbose:
        print(f"  → Base prompt: {base_prompt_tokens} tokens")

    # Read input content
    input_content = read_file_safely(input_data)
    if verbose:
        print(f"📄 Loaded: {len(input_content):,} characters")
    logger.info(f"Input loaded: {len(input_content)} characters")

    # Handle frontmatter parsing and metadata processing for --explain mode
    metadata = {}
    content_to_chunk = input_content

    if explain:
        if verbose:
            print("🔍 Parsing frontmatter...")

        # Parse frontmatter
        metadata, content_to_chunk = parse_frontmatter_content(input_content)
        logger.info(
            f"Frontmatter parsed: {len(metadata)} fields, {len(content_to_chunk)} content chars"
        )

        if metadata and verbose:
            print(f"📋 Metadata found: {list(metadata.keys())}")

        # Check metadata completeness
        is_complete, missing_fields = check_metadata_completeness(metadata)

        if not is_complete:
            if verbose:
                print(f"⚠️  Missing metadata fields: {missing_fields}")

            # Create chunks first to get the first chunk for explanation
            temp_chunks = create_chunks(content_to_chunk, data_format, chunk_size)

            if temp_chunks:
                if verbose:
                    print("🤖 Generating missing metadata with LLM...")

                # Skip metadata explanation in dry-run mode
                if dry_run:
                    if verbose:
                        print("  → Skipping metadata generation (dry-run mode)")
                    generated_metadata = {}
                else:
                    # Initialize Cerebras client for explanation
                    try:
                        client = Cerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))

                        # Generate missing metadata
                        generated_metadata = explain_metadata_with_llm(
                            client=client,
                            existing_metadata=metadata,
                            first_chunk_text=temp_chunks[0].text,
                            model=model,
                            temp=temp,
                            top_p=top_p,
                        )

                        # Update metadata with generated fields
                        if generated_metadata:
                            metadata.update(generated_metadata)
                            logger.info(
                                f"Metadata updated with generated fields: {list(generated_metadata.keys())}"
                            )
                            if verbose:
                                print(
                                    f"✅ Generated metadata: {list(generated_metadata.keys())}"
                                )
                        else:
                            logger.warning("No metadata generated by LLM")

                    except Exception as e:
                        logger.error(f"Failed to generate metadata: {e}")
                        if verbose:
                            print(f"❌ Metadata generation failed: {e}")
        else:
            if verbose:
                print("✅ All required metadata fields present, skipping explanation")

    # Create chunks (use already-created chunks if we did explanation, otherwise create new)
    if explain and "temp_chunks" in locals():
        chunks = temp_chunks
        if verbose:
            print(f"✂️  Using chunks from metadata processing...")
    else:
        if verbose:
            print(f"✂️  Creating chunks using {data_format} mode...")
        chunks = create_chunks(content_to_chunk, data_format, chunk_size)

    if not chunks:
        print("⚠️  No chunks created - input may be empty")
        logger.warning("No chunks created - input may be empty")
        write_output_atomically("", output_data, metadata if explain else None)
        return

    if verbose:
        print(
            f"📦 Created {len(chunks)} chunks (avg: {sum(c.token_count for c in chunks) // len(chunks):,} tokens each)"
        )
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            print(f"  → Chunk {i + 1}: {chunk.token_count:,} tokens")
        if len(chunks) > 3:
            print(f"  → ... and {len(chunks) - 3} more chunks")

        print(f"\n🚀 Starting processing with {model}...")

    # If dry-run mode, display chunk analysis and exit
    if dry_run:
        print("\n🔍 DRY-RUN MODE - No API calls will be made\n")

        # Display chunk analysis
        print(f"📊 Chunking Analysis:")
        print(f"  • Chunking mode: {data_format}")
        print(f"  • Total chunks: {len(chunks)}")
        print(f"  • Total input tokens: {sum(c.token_count for c in chunks):,}")
        print(
            f"  • Average chunk size: {sum(c.token_count for c in chunks) // len(chunks):,} tokens"
        )
        print(f"  • Max chunk size: {max(c.token_count for c in chunks):,} tokens")
        print(f"  • Min chunk size: {min(c.token_count for c in chunks):,} tokens")

        # Show sample of what would be sent for each chunk
        print(f"\n📋 Sample API Request Structure:")

        for i, chunk in enumerate(chunks[:2]):  # Show first 2 chunks as samples
            print(f"\n── Chunk {i + 1}/{len(chunks)} ──")

            # Build sample messages
            continuity_block = ""
            if i > 0 and sample_size > 0:
                # Simulate continuity from previous chunk
                continuity_block = "[Continuity context would be added here]"

            messages, total_tokens = prepare_chunk_messages(
                base_prompt,
                chunk,
                continuity_block,
                base_prompt_tokens,
                metadata if explain else None,
            )

            print(f"  Input tokens: {total_tokens}")
            print(
                f"  Max completion tokens: {calculate_completion_budget(chunk.token_count, max_tokens_ratio)}"
            )

            # Show message structure
            print(f"  Messages structure:")
            print(f"    • System prompt: {base_prompt_tokens} tokens")
            if metadata and explain:
                print(
                    f"    • Metadata context: {len(encode_text(json.dumps(metadata, separators=(',', ':'))))} tokens"
                )
            if continuity_block:
                print(f"    • Continuity context: {sample_size} tokens (estimated)")
            print(f"    • User content: {chunk.token_count} tokens")

            # Show preview of chunk content
            preview_lines = chunk.text.split("\n")[:5]
            preview = "\n".join(preview_lines)
            if len(preview) > 200:
                preview = preview[:200] + "..."
            print(f"\n  Chunk preview:")
            for line in preview.split("\n"):
                print(f"    │ {line}")

            if i == 1:
                print(f"\n  [... {len(chunks) - 2} more chunks would follow ...]")
                break

        # Summary
        print(f"\n✅ Dry-run complete - no API calls were made")
        print(f"   Total estimated API calls: {len(chunks)}")
        print(
            f"   Estimated total input tokens: {sum(c.token_count for c in chunks) + len(chunks) * base_prompt_tokens:,}"
        )

        # Exit after dry-run
        return

    # Initialize Cerebras client (only if not dry-run)
    try:
        client = Cerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))
        logger.debug("Cerebras client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Cerebras client: {e}")
        sys.exit(1)

    # Process all chunks
    logger.info(f"Starting processing of {len(chunks)} chunks")
    start_time = time.time()

    state = ProcessingState()
    results = []
    last_rate_status = RateLimitStatus()

    # Create progress bar for non-verbose mode
    progress_bar = (
        None
        if verbose
        else tqdm(total=len(chunks), desc="Processing chunks", unit="chunk")
    )

    for i, chunk in enumerate(chunks):
        # Show progress differently based on verbose mode
        if verbose:
            print(
                f"[{i + 1}/{len(chunks)}] Processing chunk ({chunk.token_count} tokens)..."
            )

        logger.info(
            f"Processing chunk {i + 1}/{len(chunks)} ({chunk.token_count} tokens)"
        )

        try:
            # Build continuity block if this isn't the first chunk
            continuity_block = ""
            continuity_tokens = 0
            if (
                i > 0
                and sample_size > 0
                and state.prev_input_tokens
                and state.prev_output_tokens
            ):
                if verbose:
                    print(
                        f"  → Building continuity from previous {len(state.prev_input_tokens)} input + {len(state.prev_output_tokens)} output tokens"
                    )

                input_example = extract_continuity_examples(
                    state.prev_input_text, state.prev_input_tokens, sample_size
                )
                output_example = extract_continuity_examples(
                    state.prev_output_text, state.prev_output_tokens, sample_size
                )

                if input_example and output_example:
                    continuity_block = build_continuity_block(
                        input_example, output_example
                    )
                    # Fit within token budget
                    base_tokens = base_prompt_tokens + chunk.token_count
                    continuity_block = fit_continuity_to_budget(
                        continuity_block, base_tokens
                    )
                    continuity_tokens = (
                        len(encode_text(continuity_block)) if continuity_block else 0
                    )

                    if verbose and continuity_block:
                        print(f"  → Continuity added: {continuity_tokens} tokens")
                    elif verbose:
                        print(f"  → Continuity dropped (budget exceeded)")

            # Prepare messages
            messages, total_input_tokens = prepare_chunk_messages(
                base_prompt,
                chunk,
                continuity_block,
                base_prompt_tokens,
                metadata if explain else None,
            )

            # Calculate completion budget
            max_completion_tokens = calculate_completion_budget(
                chunk.token_count, max_tokens_ratio
            )

            if verbose:
                print(
                    f"  → Request: {total_input_tokens} input tokens → max {max_completion_tokens} completion tokens"
                )

            # Apply rate limiting delay if needed
            if i > 0:  # Don't delay before first chunk
                next_chunk_tokens = chunks[i].token_count if i < len(chunks) - 1 else 0
                delay = calculate_backoff_delay(
                    last_rate_status, next_chunk_tokens, state
                )
                if delay > 0:
                    if verbose:
                        print(f"  → Rate limit delay: {delay:.1f}s")
                    logger.info(f"Rate limit delay: {delay:.1f}s")
                    time.sleep(delay)

            # Make API request
            logger.debug(
                f"Making Cerebras request: {total_input_tokens} input tokens, "
                f"{max_completion_tokens} max completion tokens"
            )

            if verbose:
                print(f"  → Calling Cerebras API...")

            response_text, rate_status = make_cerebras_request(
                client, messages, model, max_completion_tokens, temp, top_p
            )

            # Update state for next iteration
            state.prev_input_text = chunk.text
            state.prev_input_tokens = encode_text(chunk.text)
            state.prev_output_text = response_text
            state.prev_output_tokens = encode_text(response_text)

            state.total_input_tokens += total_input_tokens
            state.total_output_tokens += len(state.prev_output_tokens)
            state.chunks_processed += 1

            results.append(response_text)
            last_rate_status = rate_status

            # Show completion progress
            if verbose:
                print(
                    f"  ✓ Chunk {i + 1} complete: {len(state.prev_output_tokens)} tokens generated"
                )
                if rate_status.headers_parsed:
                    print(
                        f"  → Rate status: {rate_status.requests_remaining} requests, {rate_status.tokens_remaining} tokens remaining"
                    )
            elif progress_bar:
                progress_bar.update(1)

            logger.info(
                f"Chunk {i + 1} complete: {len(response_text)} chars, "
                f"{len(state.prev_output_tokens)} tokens generated"
            )

        except Exception as e:
            if verbose:
                print(f"  ✗ Chunk {i + 1} failed: {str(e)}")
            elif progress_bar:
                progress_bar.update(1)

            logger.error(f"Failed to process chunk {i + 1}: {e}")
            # For now, continue with remaining chunks rather than failing entirely
            results.append(f"[ERROR: Chunk {i + 1} failed - {str(e)}]")

    # Close progress bar
    if progress_bar:
        progress_bar.close()

    # Combine all results
    final_output = "".join(results)
    processing_time = time.time() - start_time

    # Write output atomically
    print(f"💾 Saved: {output_data}")
    write_output_atomically(final_output, output_data, metadata if explain else None)

    # Show remaining daily requests from the last chunk's rate limit headers
    if last_rate_status.headers_parsed and last_rate_status.requests_remaining is not None:
        # Show remaining daily requests from rate limit headers
        print(f"📊 Remaining today: {last_rate_status.requests_remaining} requests")

        # If we're getting close to the limit, show a warning
        if last_rate_status.requests_limit > 0:
            usage_percent = ((last_rate_status.requests_limit - last_rate_status.requests_remaining)
                           / last_rate_status.requests_limit * 100)
            if usage_percent > 80:
                print(f"⚠️  Daily quota {usage_percent:.1f}% used")

    # Show final statistics only in verbose mode
    if verbose:
        print(f"\n📊 Processing Summary:")
        print(f"  • Time: {processing_time:.1f}s")
        print(f"  • Chunks: {state.chunks_processed}/{len(chunks)} processed")
        print(f"  • Input tokens: {state.total_input_tokens:,}")
        print(f"  • Output tokens: {state.total_output_tokens:,}")
        print(f"  • Output size: {len(final_output):,} characters")
        print(
            f"  • Average chunk size: {state.total_input_tokens // len(chunks) if chunks else 0:,} tokens"
        )
        print(
            f"  • Average response size: {state.total_output_tokens // state.chunks_processed if state.chunks_processed else 0:,} tokens"
        )
        print(
            f"  • Processing rate: {state.total_input_tokens / processing_time:.0f} tokens/second"
        )
        print(f"  • File updated: {output_data}")

    # Log final statistics
    logger.info(f"Processing complete in {processing_time:.1f}s")
    logger.info(f"Total input tokens: {state.total_input_tokens}")
    logger.info(f"Total output tokens: {state.total_output_tokens}")
    logger.info(f"Chunks processed: {state.chunks_processed}/{len(chunks)}")
    logger.info(f"Output written to: {output_data}")


if __name__ == "__main__":
    fire.Fire(run)
