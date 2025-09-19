# cereproc.py Technical Specification

## Overview

`cereproc.py` is a Fire-based CLI tool that processes large input documents by intelligently chunking them into model-sized segments, sending each chunk to Cerebras `qwen-3-coder-480b` for processing, and concatenating the completions into a single output file. The tool emphasizes performance optimization within API rate limits while maintaining logical text continuity.

## Core Architecture

### Dependencies
- `python-dotenv`: Environment variable management
- `semantic-text-splitter`: Intelligent text segmentation
- `qwen-tokenizer`: Token counting and encoding/decoding
- `fire`: CLI interface framework
- `cerebras-cloud-sdk-python`: API client
- `loguru`: Simple logging
- `tenacity`: Retry mechanisms

### Design Principles
- Single-file implementation for simplicity
- Functional approach with minimal classes
- Aggressive performance optimization within rate limits
- Robust error handling without enterprise bloat
- Token-accurate accounting throughout

## API Constraints & Limits

### Model Specifications
- **Model**: `qwen-3-coder-480b` (overridable via `--model`)
- **Max completion tokens**: 40,000 (hard upper bound per request)
- **Max input tokens**: 32,000 (prompt + chunk + continuity additions)
- **Tokenization**: `qwen_tokenizer.encode(text)` for all counts

### Rate Limit Handling
- Parse response headers for rate limit information
- Implement adaptive backoff based on remaining quota
- Queue management for optimal throughput
- Graceful degradation when limits approached

## CLI Interface Specification

### Required Parameters
```bash
cereproc.py --input_data path/to/input.txt
```

### Optional Parameters
```bash
--output_data path/to/output.txt    # Default: overwrite input_data
--file_prompt path/to/prompt.txt    # Initial instruction file
--text_prompt "instruction text"    # Freeform instruction text
--chunk_size 32000                  # Target chunk size in tokens
--max_tokens_ratio 100              # Completion budget as % of chunk size
--data_format text|semantic|markdown|code  # Chunking strategy
--example_size 200                  # Continuity example token count
--temp 0.7                         # Model temperature
--top_p 0.8                        # Model top-p
--model qwen-3-coder-480b          # Model override
--verbose                          # Enable debug logging
```

## Prompt Assembly Strategy

### Base Prompt Construction
```python
def build_base_prompt(file_prompt_path: str | None, text_prompt: str | None) -> str:
    """Assemble base prompt from file and text components."""
    base_prompt = ""

    if file_prompt_path:
        base_prompt += read_file(file_prompt_path)

    base_prompt += "\n\n"

    if text_prompt:
        base_prompt += text_prompt

    return base_prompt
```

### Message Structure
```python
messages = [
    {"role": "system", "content": base_prompt},
    {"role": "user", "content": continuity_block + current_chunk}
]
```

## Chunking Strategies

### Text Mode (`data_format="text"`)
```python
def chunk_text_mode(content: str, chunk_size: int) -> list[Chunk]:
    """Line-based greedy accumulation respecting token limits."""
    chunks = []
    current_chunk = ""
    current_tokens = 0

    for line in content.splitlines(keepends=True):
        line_tokens = len(qwen_tokenizer.encode(line))

        if current_tokens + line_tokens > chunk_size and current_chunk:
            chunks.append(Chunk(current_chunk, current_tokens))
            current_chunk = line
            current_tokens = line_tokens
        else:
            current_chunk += line
            current_tokens += line_tokens

    if current_chunk:
        chunks.append(Chunk(current_chunk, current_tokens))

    return chunks
```

### Semantic Mode (`data_format="semantic"`)
```python
def chunk_semantic_mode(content: str, chunk_size: int) -> list[Chunk]:
    """Use semantic-text-splitter with token callback."""
    splitter = TextSplitter.from_callback(
        lambda s: len(qwen_tokenizer.encode(s)),
        chunk_size
    )

    chunk_texts = splitter.chunks(content)
    return [
        Chunk(text, len(qwen_tokenizer.encode(text)))
        for text in chunk_texts
    ]
```

### Markdown Mode (`data_format="markdown"`)
```python
def chunk_markdown_mode(content: str, chunk_size: int) -> list[Chunk]:
    """Use MarkdownSplitter with token callback."""
    splitter = MarkdownSplitter.from_callback(
        lambda s: len(qwen_tokenizer.encode(s)),
        chunk_size
    )

    chunk_texts = splitter.chunks(content)
    return [
        Chunk(text, len(qwen_tokenizer.encode(text)))
        for text in chunk_texts
    ]
```

### Code Mode (`data_format="code"`)
```python
def chunk_code_mode(content: str, chunk_size: int) -> list[Chunk]:
    """Code-aware chunking with fallback to text mode."""
    # Prefer semantic splitter if code-aware mode available
    # Fallback: bias splits at blank lines and ``` boundaries
    return chunk_text_mode_with_code_bias(content, chunk_size)
```

## Continuity System

### Continuity Block Template
```python
CONTINUITY_TEMPLATE = """Our current input text chunk is the immediate continuation of this input text chunk:

<previous_input>
(...){input_example}
</previous_input>

and the previous input chunk has been processed like so:

<previous_output>
(...){output_example}
</previous_output>

Please process our current input text analogically, and maintain logical and stylistic continuity of the text."""
```

### Example Extraction
```python
def extract_continuity_examples(
    prev_input: str,
    prev_output: str,
    example_size: int
) -> tuple[str, str]:
    """Extract last N tokens from previous input/output."""
    input_tokens = qwen_tokenizer.encode(prev_input)
    output_tokens = qwen_tokenizer.encode(prev_output)

    input_example_tokens = input_tokens[-example_size:]
    output_example_tokens = output_tokens[-example_size:]

    # Convert back to text (with fallback handling)
    input_example = decode_tokens_safely(input_example_tokens)
    output_example = decode_tokens_safely(output_example_tokens)

    return input_example, output_example
```

### Continuity Truncation
```python
def fit_continuity_to_budget(
    base_input_tokens: int,
    continuity_block: str,
    max_input_tokens: int = 32000
) -> str:
    """Truncate continuity examples to fit within token budget."""
    if base_input_tokens + len(qwen_tokenizer.encode(continuity_block)) <= max_input_tokens:
        return continuity_block

    available_tokens = max_input_tokens - base_input_tokens
    if available_tokens <= 0:
        return ""  # Drop continuity entirely

    # Proportionally reduce input/output examples
    return truncate_continuity_proportionally(continuity_block, available_tokens)
```

## Completion Token Budget

### Budget Calculation
```python
def calculate_completion_budget(
    chunk_tokens: int,
    continuity_tokens: int,
    max_tokens_ratio: int
) -> int:
    """Calculate max_completion_tokens for this chunk."""
    total_input_tokens = chunk_tokens + continuity_tokens

    # Calculate based on ratio
    requested_tokens = (chunk_tokens * max_tokens_ratio) // 100

    # Enforce hard limit
    max_completion_tokens = min(40000, requested_tokens)

    # Ensure total doesn't exceed theoretical limits
    return max_completion_tokens
```

## API Interaction & Rate Limiting

### Rate Limit Monitoring
```python
@dataclass
class RateLimitStatus:
    requests_remaining: int
    tokens_remaining: int
    reset_time: datetime

def parse_rate_limit_headers(response_headers: dict) -> RateLimitStatus:
    """Extract rate limit info from response headers."""
    return RateLimitStatus(
        requests_remaining=int(response_headers.get('x-ratelimit-remaining-requests', 0)),
        tokens_remaining=int(response_headers.get('x-ratelimit-remaining-tokens', 0)),
        reset_time=parse_reset_time(response_headers.get('x-ratelimit-reset'))
    )
```

### Adaptive Backoff
```python
def calculate_backoff_delay(rate_status: RateLimitStatus, chunk_tokens: int) -> float:
    """Calculate optimal delay based on rate limit status."""
    if rate_status.tokens_remaining < chunk_tokens:
        # Wait until reset
        return (rate_status.reset_time - datetime.now()).total_seconds()

    if rate_status.requests_remaining < 10:
        # Conservative delay when requests running low
        return 2.0

    return 0.1  # Minimal delay for optimal throughput
```

### Streaming Response Handler
```python
def process_chunk_with_streaming(
    messages: list[dict],
    max_completion_tokens: int,
    temp: float,
    top_p: float
) -> tuple[str, RateLimitStatus]:
    """Process single chunk with streaming response."""

    stream = client.chat.completions.create(
        messages=messages,
        model=model,
        stream=True,
        max_completion_tokens=max_completion_tokens,
        temperature=temp,
        top_p=top_p
    )

    response_text = ""
    rate_status = None

    for chunk in stream:
        if chunk.choices[0].delta.content:
            response_text += chunk.choices[0].delta.content

        # Extract rate limit info from headers if available
        if hasattr(chunk, 'headers'):
            rate_status = parse_rate_limit_headers(chunk.headers)

    return response_text, rate_status
```

## Error Handling & Resilience

### Retry Strategy
```python
@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=60),
    retry=tenacity.retry_if_exception_type((ConnectionError, TimeoutError))
)
def make_api_request_with_retry(messages, **kwargs):
    """API request with exponential backoff retry."""
    return client.chat.completions.create(messages=messages, **kwargs)
```

### Validation & Edge Cases
```python
def validate_inputs(args) -> None:
    """Validate all input parameters and environment."""
    if not os.getenv('CEREBRAS_API_KEY'):
        raise ValueError("CEREBRAS_API_KEY environment variable required")

    if not Path(args.input_data).exists():
        raise FileNotFoundError(f"Input file not found: {args.input_data}")

    if args.chunk_size > 32000:
        logger.warning("chunk_size > 32000 may cause API errors")

    if args.example_size > args.chunk_size // 2:
        logger.warning("example_size very large relative to chunk_size")
```

## Output Assembly & File Operations

### Atomic File Writing
```python
def write_output_atomically(content: str, output_path: Path) -> None:
    """Write output using temporary file for atomicity."""
    temp_path = output_path.with_suffix(output_path.suffix + '.tmp')

    try:
        temp_path.write_text(content, encoding='utf-8')
        temp_path.replace(output_path)  # Atomic on most filesystems
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise e
```

### Progress Tracking
```python
def process_all_chunks(chunks: list[Chunk], **kwargs) -> str:
    """Process all chunks with progress tracking and rate limiting."""
    results = []

    for i, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {i+1}/{len(chunks)} ({chunk.token_count} tokens)")

        # Build messages with continuity
        messages = build_messages_for_chunk(chunk, i, results)

        # Calculate budget
        max_tokens = calculate_completion_budget(chunk.token_count, ...)

        # Process with rate limiting
        result, rate_status = process_chunk_with_streaming(messages, max_tokens, ...)
        results.append(result)

        # Adaptive delay based on rate limits
        if i < len(chunks) - 1:  # Don't delay after last chunk
            delay = calculate_backoff_delay(rate_status, chunks[i+1].token_count)
            if delay > 0:
                logger.debug(f"Rate limit delay: {delay:.1f}s")
                time.sleep(delay)

    return "".join(results)
```

## Data Structures

### Core Data Classes
```python
@dataclass
class Chunk:
    text: str
    token_count: int

@dataclass
class ProcessingContext:
    base_prompt: str
    chunks: list[Chunk]
    example_size: int
    max_tokens_ratio: int
    model_params: dict
```

## Testing Strategy

### Test Data Structure
```
testdata/
├── test1.md          # Primary test document
├── test.sh           # Test execution script
├── expected_out.txt  # Expected output for validation
└── prompts/
    └── test_prompt.txt
```

### Test Script Template
```bash
#!/bin/bash
# testdata/test.sh

python cereproc.py \
    --input_data testdata/test1.md \
    --output_data testdata/actual_out.txt \
    --file_prompt testdata/prompts/test_prompt.txt \
    --data_format markdown \
    --verbose

# Compare output
diff testdata/expected_out.txt testdata/actual_out.txt
```

## Performance Optimizations

### Token Caching
- Cache tokenization results for repeated text
- Avoid re-tokenizing unchanged continuity examples

### Batch Optimization
- Process multiple chunks in parallel when rate limits allow
- Pipeline chunk preparation while previous chunk processes

### Memory Management
- Stream large file reading to avoid memory spikes
- Clear processed chunk data promptly

## Configuration & Environment

### Environment Variables
```bash
CEREBRAS_API_KEY=csk-...           # Required: API authentication
CEREPROC_LOG_LEVEL=INFO           # Optional: logging level
CEREPROC_MAX_RETRIES=3            # Optional: retry attempts
```

### Default Configuration
```python
DEFAULT_CONFIG = {
    'chunk_size': 32000,
    'max_tokens_ratio': 100,
    'data_format': 'text',
    'example_size': 200,
    'temp': 0.7,
    'top_p': 0.8,
    'model': 'qwen-3-coder-480b'
}
```

## Implementation Notes

### Token Handling Edge Cases
- Handle tokenizer decode failures gracefully
- Fall back to character-based approximation when decode unavailable
- Validate token counts against actual API consumption

### Continuity Logic
- First chunk: no continuity block
- Subsequent chunks: extract examples from previous input/output
- Truncation: reduce input/output examples proportionally

### Error Recovery
- API failures: retry with exponential backoff
- Rate limiting: adaptive delays based on headers
- Oversized chunks: process individually with warning
- Empty input: create empty output file

This specification provides the complete technical foundation for implementing `cereproc.py` as a robust, performant, and simple CLI tool focused on its core mission of intelligent document processing through the Cerebras API.