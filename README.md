# cereproc.py

Process large documents by intelligently chunking them for Cerebras `qwen-3-coder-480b` processing with optimal performance and continuity.

## TLDR

**What it does**: Takes a large text file, splits it into model-sized chunks, sends each chunk to Cerebras for processing, and concatenates all responses into a single output file while maintaining logical continuity between chunks.

**Why it's useful**: Allows processing of documents larger than the 32K token input limit while preserving context and narrative flow through intelligent chunking and continuity examples.

## Quick Start

```bash
# Basic usage
python cereproc.py --input_data document.txt

# With custom prompt and chunking
python cereproc.py \
    --input_data large_doc.md \
    --output_data processed_doc.md \
    --file_prompt instructions.txt \
    --data_format markdown \
    --chunk_size 30000
```

## Code Structure

### Single-File Architecture
- **cereproc.py**: Complete implementation (~400-500 lines)
  - CLI interface via Fire
  - Chunking strategies (text/semantic/markdown/code)
  - Continuity system for cross-chunk context
  - Rate limit monitoring and adaptive backoff
  - Streaming API interaction with Cerebras

### Key Components

#### 1. Chunking Engine
```python
# Four chunking strategies
chunk_text_mode()      # Line-based greedy accumulation
chunk_semantic_mode()  # Semantic boundaries via semantic-text-splitter
chunk_markdown_mode()  # Markdown-aware splitting
chunk_code_mode()      # Code-aware with blank line bias
```

#### 2. Continuity System
```python
# Maintains context between chunks
extract_continuity_examples()  # Get last N tokens from prev input/output
build_continuity_block()       # Format context template
fit_continuity_to_budget()     # Truncate if needed for token limits
```

#### 3. Rate Limit Optimization
```python
parse_rate_limit_headers()    # Extract API quota info
calculate_backoff_delay()     # Adaptive delays for max throughput
process_chunk_with_streaming() # Streaming with rate monitoring
```

#### 4. Token Management
```python
# Precise token accounting throughout
qwen_tokenizer.encode()       # All token counting
calculate_completion_budget() # Per-chunk token allocation
validate_token_limits()       # Enforce 32K input / 40K output limits
```

## Functionality

### Core Features
- **Intelligent Chunking**: 4 modes (text/semantic/markdown/code) with token-accurate splitting
- **Continuity Preservation**: Last N tokens from previous chunks provide context
- **Rate Limit Optimization**: Parse API headers and adapt delays for maximum throughput
- **Streaming Processing**: Real-time output with progress tracking
- **Atomic Output**: Safe file writing with temporary files

### CLI Parameters
```bash
--input_data FILE         # Input document to process
--output_data FILE        # Output file (default: overwrite input)
--file_prompt FILE        # Instructions from file
--text_prompt TEXT        # Additional instruction text
--chunk_size INT          # Target tokens per chunk (default: 32000)
--max_tokens_ratio INT    # Completion budget % (default: 100)
--data_format MODE        # text|semantic|markdown|code (default: text)
--example_size INT        # Continuity example tokens (default: 200)
--temp FLOAT             # Model temperature (default: 0.7)
--top_p FLOAT            # Model top-p (default: 0.8)
```

### Dependencies
```python
# Required packages
cerebras-cloud-sdk-python  # API client
semantic-text-splitter     # Intelligent text chunking
qwen-tokenizer            # Token counting for Qwen models
fire                      # CLI framework
loguru                    # Simple logging
tenacity                  # Retry mechanisms
python-dotenv             # Environment management
```

## Performance Features

### Rate Limit Intelligence
- Monitors `x-ratelimit-remaining-requests` and `x-ratelimit-remaining-tokens` headers
- Calculates optimal delays to maximize throughput within limits
- Adaptive backoff when approaching quota limits

### Memory Efficiency
- Streams large files without loading entirely into memory
- Clears processed chunks promptly
- Caches tokenization results for repeated text

### Error Resilience
- Exponential backoff retry for transient failures
- Graceful handling of oversized chunks
- Continuity truncation when hitting token limits
- Atomic file operations prevent data loss

## Testing

```bash
# Test with provided data
cd testdata
./test.sh

# Manual testing
python cereproc.py --input_data testdata/test1.md --output_data out.txt --verbose
```

## Environment Setup

```bash
export CEREBRAS_API_KEY="csk-..."  # Required
export CEREPROC_LOG_LEVEL="INFO"  # Optional
```

## Use Cases

- **Document Processing**: Transform large reports, articles, or books
- **Code Analysis**: Process entire codebases with code-aware chunking
- **Content Generation**: Create long-form content with consistent style
- **Translation**: Translate large documents while preserving context
- **Summarization**: Generate summaries of lengthy documents

The tool prioritizes simplicity and performance while providing sophisticated chunking and continuity features for high-quality results on large documents.