#!/usr/bin/env python3
# this_file: src/cerebrate_file/chunking.py

"""Text chunking strategies for cerebrate_file package.

This module provides various strategies for splitting large documents into
smaller chunks that fit within model context windows while preserving
semantic and structural boundaries.
"""

from loguru import logger

from .constants import CHARS_PER_TOKEN_FALLBACK, COMPILED_BOUNDARY_PATTERNS, ChunkingError
from .models import Chunk
from .tokenizer import encode_text

__all__ = [
    "ChunkingStrategy",
    "CodeChunker",
    "MarkdownChunker",
    "SemanticChunker",
    "TextChunker",
    "XmlChunker",
    "create_chunks",
    "get_chunking_strategy",
]


class ChunkingStrategy:
    """Base class for chunking strategies."""

    def __init__(self, chunk_size: int) -> None:
        """Initialize the chunking strategy.

        Args:
            chunk_size: Maximum tokens per chunk
        """
        if chunk_size <= 0:
            raise ChunkingError("chunk_size must be positive")
        self.chunk_size = chunk_size

    def chunk(self, content: str) -> list[Chunk]:
        """Split content into chunks.

        Args:
            content: Input text content

        Returns:
            List of Chunk objects

        Raises:
            ChunkingError: If chunking fails
        """
        raise NotImplementedError("Subclasses must implement chunk method")

    def _create_chunk(self, text: str) -> Chunk:
        """Create a chunk from text with token counting.

        Args:
            text: Text content for the chunk

        Returns:
            Chunk object
        """
        tokens = encode_text(text)
        return Chunk(text=text, token_count=len(tokens))

    def _handle_overlong_line(self, line: str, chunks: list[Chunk]) -> None:
        """Handle lines that exceed chunk size.

        Args:
            line: The overlong line
            chunks: List to append chunks to
        """
        line_tokens = len(encode_text(line))
        if line_tokens > self.chunk_size:
            logger.warning(
                f"Single line exceeds chunk_size ({line_tokens} > {self.chunk_size}), "
                f"processing as individual chunk"
            )
            chunks.append(self._create_chunk(line))


class TextChunker(ChunkingStrategy):
    """Line-based greedy accumulation respecting token limits."""

    def chunk(self, content: str) -> list[Chunk]:
        """Split content using line-based chunking.

        Args:
            content: Input text content

        Returns:
            List of Chunk objects
        """
        chunks = []
        lines = content.splitlines(keepends=True)

        current_chunk = ""
        current_tokens = 0

        for line in lines:
            line_tokens = len(encode_text(line))

            # If adding this line would exceed chunk size and we have content, finalize chunk
            if current_tokens + line_tokens > self.chunk_size and current_chunk:
                chunks.append(Chunk(current_chunk, current_tokens))
                current_chunk = line
                current_tokens = line_tokens
            else:
                current_chunk += line
                current_tokens += line_tokens

            # Handle overlong single lines
            if line_tokens > self.chunk_size:
                self._handle_overlong_line(line, chunks)
                if current_chunk == line:  # Reset if we just added the overlong line
                    current_chunk = ""
                    current_tokens = 0

        # Add final chunk if any content remains
        if current_chunk:
            chunks.append(Chunk(current_chunk, current_tokens))

        logger.info(f"Text mode chunking: {len(chunks)} chunks created")
        return chunks


class SemanticChunker(ChunkingStrategy):
    """Use semantic-text-splitter with token callback."""

    def chunk(self, content: str) -> list[Chunk]:
        """Split content using semantic boundaries.

        Args:
            content: Input text content

        Returns:
            List of Chunk objects
        """
        try:
            from semantic_text_splitter import TextSplitter

            # Use character-based approximation to avoid tokenizer recursion
            char_limit = self.chunk_size * CHARS_PER_TOKEN_FALLBACK
            splitter = TextSplitter(char_limit)
            chunk_texts = splitter.chunks(content)

            chunks = [self._create_chunk(text) for text in chunk_texts]

            logger.info(f"Semantic mode chunking: {len(chunks)} chunks created")
            return chunks

        except ImportError:
            logger.warning("semantic-text-splitter not available, falling back to text mode")
            return TextChunker(self.chunk_size).chunk(content)
        except Exception as e:
            logger.warning(f"Semantic chunking failed: {e}, falling back to text mode")
            return TextChunker(self.chunk_size).chunk(content)


class MarkdownChunker(ChunkingStrategy):
    """Use MarkdownSplitter with token callback."""

    def chunk(self, content: str) -> list[Chunk]:
        """Split content respecting Markdown structure.

        Args:
            content: Input text content

        Returns:
            List of Chunk objects
        """
        try:
            from semantic_text_splitter import MarkdownSplitter

            # Use character-based approximation to avoid tokenizer recursion
            char_limit = self.chunk_size * CHARS_PER_TOKEN_FALLBACK
            splitter = MarkdownSplitter(char_limit)
            chunk_texts = splitter.chunks(content)

            chunks = [self._create_chunk(text) for text in chunk_texts]

            logger.info(f"Markdown mode chunking: {len(chunks)} chunks created")
            return chunks

        except ImportError:
            logger.warning("semantic-text-splitter not available, falling back to text mode")
            return TextChunker(self.chunk_size).chunk(content)
        except Exception as e:
            logger.warning(f"Markdown chunking failed: {e}, falling back to text mode")
            return TextChunker(self.chunk_size).chunk(content)


class CodeChunker(ChunkingStrategy):
    """Code-aware chunking that respects code structure boundaries."""

    def __init__(self, chunk_size: int) -> None:
        """Initialize the code chunker.

        Args:
            chunk_size: Maximum tokens per chunk
        """
        super().__init__(chunk_size)
        self.boundary_patterns = COMPILED_BOUNDARY_PATTERNS

    def _is_good_split_point(
        self, line_idx: int, line: str, brace_depth: int, paren_depth: int, in_string: bool
    ) -> bool:
        """Determine if this is a good place to split chunks.

        Args:
            line_idx: Index of the line
            line: The line content
            brace_depth: Current brace nesting depth
            paren_depth: Current parenthesis nesting depth
            in_string: Whether we're inside a string literal

        Returns:
            True if this is a good split point
        """
        # Don't split if we're inside nested structures
        if brace_depth > 0 or paren_depth > 0 or in_string:
            return False

        # Check if line matches any boundary pattern
        for pattern in self.boundary_patterns:
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

    def _track_code_structure(self, line: str) -> tuple[int, int, bool, str | None]:
        """Track code structure depth for better splitting decisions.

        Args:
            line: The line to analyze

        Returns:
            Tuple of (brace_depth_change, paren_depth_change, in_string, string_delimiter)
        """
        brace_change = 0
        paren_change = 0
        in_string = False
        string_delimiter = None

        for i, char in enumerate(line):
            if not in_string:
                if char in ['"', "'"]:
                    # Check if this quote is escaped
                    if i == 0 or line[i - 1] != "\\":
                        in_string = True
                        string_delimiter = char
                elif char == "{":
                    brace_change += 1
                elif char == "}":
                    brace_change -= 1
                elif char == "(":
                    paren_change += 1
                elif char == ")":
                    paren_change -= 1
            else:
                if char == string_delimiter and (i == 0 or line[i - 1] != "\\"):
                    in_string = False
                    string_delimiter = None

        return brace_change, paren_change, in_string, string_delimiter

    def chunk(self, content: str) -> list[Chunk]:
        """Split content using code-aware chunking.

        Args:
            content: Input text content

        Returns:
            List of Chunk objects
        """
        logger.debug("Using code-aware chunking strategy")

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

        for idx, line in enumerate(lines):
            # Track structure depth for better splitting decisions
            brace_change, paren_change, line_in_string, line_string_delimiter = (
                self._track_code_structure(line)
            )

            # Update global state
            brace_depth = max(0, brace_depth + brace_change)
            paren_depth = max(0, paren_depth + paren_change)

            if line_in_string:
                in_string = line_in_string
                string_delimiter = line_string_delimiter
            elif not line_in_string and string_delimiter:
                in_string = False
                string_delimiter = None

            line_tokens = len(encode_text(line))

            # Check if adding this line would exceed chunk size
            if current_tokens + line_tokens > self.chunk_size and current_chunk:
                # Look for a good split point
                if self._is_good_split_point(idx, line, brace_depth, paren_depth, in_string):
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
                            if any(pattern.match(back_line) for pattern in self.boundary_patterns):
                                # Split at this earlier good point
                                chunk_before = current_chunk[:back_idx]
                                chunk_after = current_chunk[back_idx:]

                                if chunk_before:
                                    before_tokens = sum(
                                        len(encode_text(line)) for line in chunk_before
                                    )
                                    chunks.append(Chunk("".join(chunk_before), before_tokens))

                                current_chunk = [*chunk_after, line]
                                current_tokens = sum(
                                    len(encode_text(line)) for line in current_chunk
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
            if line_tokens > self.chunk_size:
                logger.warning(
                    f"Single line exceeds chunk_size ({line_tokens} > {self.chunk_size}), "
                    f"processing as individual chunk"
                )
                if current_chunk and current_chunk[-1] == line:
                    current_chunk.pop()  # Remove the line we just added
                if current_chunk:
                    chunks.append(Chunk("".join(current_chunk), current_tokens - line_tokens))
                    current_chunk = []
                    current_tokens = 0
                chunks.append(Chunk(line, line_tokens))

        # Add any remaining content
        if current_chunk:
            chunks.append(Chunk("".join(current_chunk), current_tokens))

        logger.info(f"Code mode chunking: {len(chunks)} chunks created")
        return chunks


class XmlChunker(ChunkingStrategy):
    """XML-aware chunking that respects XML structure.

    This chunker:
    1. Checks if content is valid XML
    2. If not, wraps non-XML text in <p> tags and wraps all in <x> root
    3. Chunks the XML respecting element boundaries
    """

    def _is_valid_xml(self, content: str) -> bool:
        """Check if content is valid XML.

        Args:
            content: Content to check

        Returns:
            True if content is valid XML
        """
        import xml.etree.ElementTree as ET

        try:
            ET.fromstring(content)
            return True
        except ET.ParseError:
            return False

    def _normalize_to_xml(self, content: str) -> str:
        """Normalize content to valid XML by wrapping non-XML text in <p> tags.

        Wraps text outside tags in <p> elements and wraps everything in <x> root.
        Only wraps text at the root level (depth 0), not text inside elements.
        Example: "Hello <b>welcome</b>" → "<x><p>Hello </p><b>welcome</b></x>"

        Args:
            content: Content to normalize

        Returns:
            Normalized XML string
        """
        if self._is_valid_xml(content):
            return content

        result = []
        current_text = []
        i = 0
        depth = 0  # Track element nesting depth

        while i < len(content):
            if content[i] == "<":
                # Flush accumulated text as <p> element (only at root level)
                if current_text:
                    text = "".join(current_text)
                    if depth == 0:
                        if text.strip():  # Only wrap non-empty text
                            # Escape XML special chars in text
                            escaped = self._escape_xml_text(text)
                            result.append(f"<p>{escaped}</p>")
                        elif text:  # Preserve whitespace-only text
                            result.append(f"<p>{text}</p>")
                    else:
                        # Inside an element, keep text as-is
                        result.append(text)
                    current_text = []

                # Find end of tag
                tag_end = content.find(">", i)
                if tag_end == -1:
                    # Malformed - treat rest as text
                    current_text.append(content[i:])
                    break

                tag = content[i : tag_end + 1]

                # Check for CDATA sections
                if content[i:].startswith("<![CDATA["):
                    cdata_end = content.find("]]>", i)
                    if cdata_end != -1:
                        result.append(content[i : cdata_end + 3])
                        i = cdata_end + 3
                        continue

                # Check for comments
                if content[i:].startswith("<!--"):
                    comment_end = content.find("-->", i)
                    if comment_end != -1:
                        result.append(content[i : comment_end + 3])
                        i = comment_end + 3
                        continue

                # Check for processing instructions
                if content[i:].startswith("<?"):
                    pi_end = content.find("?>", i)
                    if pi_end != -1:
                        result.append(content[i : pi_end + 2])
                        i = pi_end + 2
                        continue

                # Track depth for opening/closing tags
                if tag.startswith("</"):
                    depth = max(0, depth - 1)
                elif not tag.endswith("/>"):
                    # Opening tag (not self-closing)
                    depth += 1

                result.append(tag)
                i = tag_end + 1
            else:
                current_text.append(content[i])
                i += 1

        # Flush remaining text
        if current_text:
            text = "".join(current_text)
            if depth == 0:
                if text.strip():
                    escaped = self._escape_xml_text(text)
                    result.append(f"<p>{escaped}</p>")
                elif text:
                    result.append(f"<p>{text}</p>")
            else:
                result.append(text)

        normalized = "".join(result)

        # Wrap in <x> root if not already valid XML
        if not self._is_valid_xml(normalized):
            normalized = f"<x>{normalized}</x>"

        return normalized

    def _escape_xml_text(self, text: str) -> str:
        """Escape XML special characters in text content.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _find_element_boundaries(self, content: str) -> list[tuple[int, int, int]]:
        """Find all top-level element boundaries in XML content.

        Args:
            content: XML content to analyze

        Returns:
            List of (start, end, depth) tuples for each element
        """
        boundaries = []
        i = 0
        depth = 0
        element_start = None

        while i < len(content):
            if content[i] == "<":
                # Skip comments, CDATA, processing instructions
                if content[i:].startswith("<!--"):
                    end = content.find("-->", i)
                    if end != -1:
                        i = end + 3
                        continue
                elif content[i:].startswith("<![CDATA["):
                    end = content.find("]]>", i)
                    if end != -1:
                        i = end + 3
                        continue
                elif content[i:].startswith("<?"):
                    end = content.find("?>", i)
                    if end != -1:
                        i = end + 2
                        continue

                tag_end = content.find(">", i)
                if tag_end == -1:
                    break

                tag = content[i : tag_end + 1]

                if tag.startswith("</"):
                    # Closing tag
                    depth -= 1
                    if depth == 0 and element_start is not None:
                        boundaries.append((element_start, tag_end + 1, 0))
                        element_start = None
                elif tag.endswith("/>"):
                    # Self-closing tag
                    if depth == 0:
                        boundaries.append((i, tag_end + 1, 0))
                else:
                    # Opening tag
                    if depth == 0:
                        element_start = i
                    depth += 1

                i = tag_end + 1
            else:
                # Text content at root level
                if depth == 0:
                    text_start = i
                    while i < len(content) and content[i] != "<":
                        i += 1
                    if i > text_start:
                        boundaries.append((text_start, i, 0))
                else:
                    i += 1

        return boundaries

    def chunk(self, content: str) -> list[Chunk]:
        """Split content using XML-aware chunking.

        Args:
            content: Input text content

        Returns:
            List of Chunk objects
        """
        logger.debug("Using XML-aware chunking strategy")

        # Normalize content to valid XML
        normalized = self._normalize_to_xml(content)
        logger.debug(f"Normalized content length: {len(normalized)}")

        # If content fits in one chunk, return it directly
        total_tokens = len(encode_text(normalized))
        if total_tokens <= self.chunk_size:
            logger.info("XML mode chunking: 1 chunk created (content fits)")
            return [self._create_chunk(normalized)]

        # Find element boundaries for chunking
        boundaries = self._find_element_boundaries(normalized)

        if not boundaries:
            # No elements found, fall back to text chunking
            logger.warning("No XML elements found, falling back to text mode")
            return TextChunker(self.chunk_size).chunk(normalized)

        chunks = []
        current_elements = []
        current_tokens = 0

        for start, end, _depth in boundaries:
            element = normalized[start:end]
            element_tokens = len(encode_text(element))

            # If single element exceeds chunk size, handle it separately
            if element_tokens > self.chunk_size:
                # First, flush current accumulated elements
                if current_elements:
                    chunk_content = self._wrap_chunk(current_elements)
                    chunks.append(self._create_chunk(chunk_content))
                    current_elements = []
                    current_tokens = 0

                # Handle overlong element
                logger.warning(
                    f"Single XML element exceeds chunk_size ({element_tokens} > {self.chunk_size}), "
                    f"processing as individual chunk"
                )
                chunk_content = self._wrap_chunk([element])
                chunks.append(self._create_chunk(chunk_content))
                continue

            # Check if adding this element would exceed chunk size
            if current_tokens + element_tokens > self.chunk_size and current_elements:
                # Finalize current chunk
                chunk_content = self._wrap_chunk(current_elements)
                chunks.append(self._create_chunk(chunk_content))
                current_elements = [element]
                current_tokens = element_tokens
            else:
                current_elements.append(element)
                current_tokens += element_tokens

        # Add remaining elements
        if current_elements:
            chunk_content = self._wrap_chunk(current_elements)
            chunks.append(self._create_chunk(chunk_content))

        logger.info(f"XML mode chunking: {len(chunks)} chunks created")
        return chunks

    def _wrap_chunk(self, elements: list[str]) -> str:
        """Wrap chunk elements in XML container.

        Args:
            elements: List of XML element strings

        Returns:
            Wrapped XML string
        """
        content = "".join(elements)
        # Check if already has root element
        if self._is_valid_xml(content):
            return content
        return f"<x>{content}</x>"


def get_chunking_strategy(data_format: str, chunk_size: int) -> ChunkingStrategy:
    """Get a chunking strategy instance.

    Args:
        data_format: Chunking strategy name
        chunk_size: Maximum tokens per chunk

    Returns:
        ChunkingStrategy instance

    Raises:
        ChunkingError: If data_format is unknown
    """
    strategies = {
        "text": TextChunker,
        "semantic": SemanticChunker,
        "markdown": MarkdownChunker,
        "code": CodeChunker,
        "xml": XmlChunker,
    }

    if data_format not in strategies:
        raise ChunkingError(
            f"Unknown data_format: {data_format}. Must be one of: {list(strategies.keys())}"
        )

    return strategies[data_format](chunk_size)


def create_chunks(content: str, data_format: str, chunk_size: int) -> list[Chunk]:
    """Create chunks using the specified strategy.

    Args:
        content: Input text content
        data_format: Chunking strategy (text|semantic|markdown|code|xml)
        chunk_size: Maximum tokens per chunk

    Returns:
        List of Chunk objects

    Raises:
        ChunkingError: If chunking fails
    """
    logger.info(f"Creating chunks using {data_format} mode, max {chunk_size} tokens")

    try:
        strategy = get_chunking_strategy(data_format, chunk_size)
        chunks = strategy.chunk(content)

        # Log chunking statistics
        if chunks:
            total_tokens = sum(chunk.token_count for chunk in chunks)
            avg_tokens = total_tokens / len(chunks)
            logger.info(
                f"Chunking complete: {len(chunks)} chunks, {total_tokens} total tokens, "
                f"{avg_tokens:.1f} avg tokens per chunk"
            )
        else:
            logger.warning("No chunks created - input may be empty")

        return chunks

    except Exception as e:
        raise ChunkingError(f"Chunking failed with {data_format} strategy: {e}") from e
