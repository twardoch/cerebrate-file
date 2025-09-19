---
layout: default
title: CLI Reference
nav_order: 4
---

# CLI Reference
{: .no_toc }

Complete reference for all command-line options
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Synopsis

```bash
cerebrate-file INPUT_DATA [OPTIONS]
```

Process large documents by chunking for Cerebras qwen-3-coder-480b model.

## Positional Arguments

### INPUT_DATA
{: .d-inline-block }

Required
{: .label .label-red }

Path to input file or directory to process.

- **Type**: String (file or directory path)
- **Required**: Yes
- **Examples**:
  - `document.md` - Single file
  - `.` - Current directory (with `--recurse`)
  - `/path/to/files` - Specific directory

## Optional Arguments

### Core Options

#### --output, -o OUTPUT_DATA

Path to output file or directory.

- **Type**: String (file or directory path)
- **Default**: Overwrites input file
- **Examples**:
  - `--output processed.md`
  - `-o ./output/`
  - `--output /tmp/results.txt`

When processing directories with `--recurse`, the output path should be a directory. The original directory structure will be replicated.

#### --prompt, -p PROMPT

Freeform instruction text for the AI model.

- **Type**: String
- **Default**: None
- **Examples**:
  - `--prompt "Summarize each section"`
  - `-p "Translate to Spanish"`
  - `--prompt "Add detailed comments"`

This is appended after any `--file_prompt` content with two newlines.

#### --file_prompt, -f FILE_PROMPT

Path to file containing instructions for the AI model.

- **Type**: String (file path)
- **Default**: None
- **Example**: `--file_prompt instructions.md`

Useful for complex or reusable instructions. The file content is loaded and used as the base prompt.

### Chunking Options

#### --chunk_size, -c CHUNK_SIZE

Target maximum input chunk size in tokens.

- **Type**: Integer
- **Default**: 32000
- **Range**: 1000 - 100000 (recommended: 16000 - 64000)
- **Examples**:
  - `--chunk_size 48000` - Larger chunks
  - `-c 16000` - Smaller chunks

Larger chunks preserve more context but may hit token limits. Smaller chunks process faster but may lose context.

#### --data_format DATA_FORMAT

Chunking strategy for different content types.

- **Type**: String
- **Default**: `markdown`
- **Options**:
  - `text` - Simple line-based splitting
  - `semantic` - Paragraph-aware splitting
  - `markdown` - Markdown structure-aware (headers, code blocks)
  - `code` - Code structure-aware (functions, classes)
- **Examples**:
  - `--data_format code` - For source files
  - `--data_format semantic` - For articles

#### --sample_size, -s SAMPLE_SIZE

Number of tokens for continuity examples between chunks.

- **Type**: Integer
- **Default**: 200
- **Range**: 0 - 1000
- **Examples**:
  - `--sample_size 500` - More context overlap
  - `-s 50` - Minimal overlap

Higher values maintain better continuity but reduce available tokens for new content.

#### --max_tokens_ratio MAX_TOKENS_RATIO

Completion budget as percentage of chunk size.

- **Type**: Integer
- **Default**: 100
- **Range**: 10 - 200
- **Examples**:
  - `--max_tokens_ratio 50` - Output half the input size
  - `--max_tokens_ratio 150` - Allow expansion

Controls how much output the model can generate per chunk.

### Recursive Processing Options

#### --recurse PATTERN

Enable recursive file processing with glob pattern.

- **Type**: String (glob pattern)
- **Default**: None (single file mode)
- **Examples**:
  - `--recurse "*.md"` - All markdown files in current directory
  - `--recurse "**/*.py"` - All Python files recursively
  - `--recurse "**/*.{js,ts}"` - Multiple extensions
  - `--recurse "src/**/*.txt"` - Specific subdirectory

Patterns support:
- `*` - Match any characters (except path separator)
- `**` - Match any characters including path separators
- `?` - Match single character
- `[seq]` - Match character in sequence
- `{opt1,opt2}` - Match any of the options

#### --workers WORKERS

Number of parallel workers for multi-file processing.

- **Type**: Integer
- **Default**: 4
- **Range**: 0 - 32
- **Special Values**:
  - `0` - Auto-detect based on CPU cores
  - `1` - Sequential processing
- **Examples**:
  - `--workers 8` - Use 8 parallel workers
  - `--workers 1` - Process files sequentially

More workers speed up processing but increase API request rate.

### Model Parameters

#### --model MODEL

Cerebras model to use.

- **Type**: String
- **Default**: `qwen-3-coder-480b`
- **Currently Supported**: `qwen-3-coder-480b`
- **Example**: `--model qwen-3-coder-480b`

#### --temp TEMP

Model temperature for response generation.

- **Type**: Float
- **Default**: 0.7
- **Range**: 0.0 - 2.0
- **Examples**:
  - `--temp 0.3` - More deterministic
  - `--temp 0.9` - More creative
  - `--temp 0.0` - Most deterministic

Higher values increase creativity and variation, lower values increase consistency.

#### --top_p TOP_P

Nucleus sampling parameter.

- **Type**: Float
- **Default**: 0.8
- **Range**: 0.0 - 1.0
- **Examples**:
  - `--top_p 0.9` - Wider token selection
  - `--top_p 0.5` - Narrower token selection

Controls diversity by limiting token selection to cumulative probability.

### Output Options

#### --verbose, -v

Enable detailed debug logging.

- **Type**: Boolean flag
- **Default**: False
- **Usage**: `--verbose` or `-v`

Shows:
- Token counts for each chunk
- API request/response details
- Rate limit information
- Processing timestamps
- Detailed error messages

#### --explain, -e

Enable metadata extraction and processing.

- **Type**: Boolean flag
- **Default**: False
- **Usage**: `--explain` or `-e`

Extracts/generates:
- Document title
- Author information
- Document ID
- Content type
- Date information

#### --dry_run

Perform chunking without making API calls.

- **Type**: Boolean flag
- **Default**: False
- **Usage**: `--dry_run`

Useful for:
- Testing chunk configurations
- Validating patterns
- Debugging issues
- Estimating costs

Shows chunk information and token counts without processing.

## Environment Variables

### CEREBRAS_API_KEY

Your Cerebras API key (required).

```bash
export CEREBRAS_API_KEY="csk-..."
```

Can also be set in a `.env` file in the current directory.

### HTTP_PROXY / HTTPS_PROXY

Optional proxy configuration.

```bash
export HTTPS_PROXY="http://proxy.example.com:8080"
```

## Exit Codes

- **0**: Success
- **1**: General error
- **2**: Invalid arguments
- **3**: API key not found
- **4**: File not found
- **5**: Permission denied
- **6**: API error
- **7**: Rate limit exceeded
- **8**: Network error

## Examples

### Basic Processing

```bash
# Simple processing
cerebrate-file document.md

# With output file
cerebrate-file input.txt --output output.txt

# With instructions
cerebrate-file report.md --prompt "Summarize to 500 words"
```

### Advanced Processing

```bash
# Complex instructions from file
cerebrate-file thesis.md \
  --file_prompt style_guide.md \
  --prompt "Also fix grammar" \
  --output edited_thesis.md

# Optimized for code
cerebrate-file app.py \
  --data_format code \
  --chunk_size 24000 \
  --prompt "Add type hints"
```

### Recursive Processing

```bash
# Process all markdown files
cerebrate-file . \
  --output ./processed \
  --recurse "**/*.md" \
  --workers 8

# Process specific patterns
cerebrate-file ./src \
  --output ./docs \
  --recurse "**/*.{js,jsx,ts,tsx}" \
  --prompt "Generate JSDoc comments"
```

### Fine-tuning

```bash
# High-quality processing
cerebrate-file important.md \
  --chunk_size 48000 \
  --sample_size 500 \
  --temp 0.3 \
  --top_p 0.7

# Fast processing
cerebrate-file large_file.txt \
  --chunk_size 16000 \
  --sample_size 100 \
  --max_tokens_ratio 50
```

### Debugging

```bash
# Test configuration
cerebrate-file huge.md \
  --dry_run \
  --verbose \
  --chunk_size 32000

# Detailed logging
cerebrate-file problem.md \
  --verbose \
  --output debug.md
```

## Rate Limits

Cerebras API has the following limits:

- **Per Minute**: 30 requests, 10M tokens
- **Per Day**: 1000 requests

The tool automatically handles rate limiting with:
- Exponential backoff
- Automatic retry
- Clear status messages
- Remaining quota display

## Performance Tips

1. **Chunk Size**: Larger chunks (48K-64K) preserve context better
2. **Workers**: Use 4-8 workers for optimal throughput
3. **Sample Size**: 200-500 tokens usually sufficient
4. **Data Format**: Match format to content type
5. **Temperature**: Lower values (0.3-0.5) for consistency

## Troubleshooting

### Common Issues

**API Key not found:**
```bash
export CEREBRAS_API_KEY="csk-your-key"
```

**Rate limit exceeded:**
- Wait for limit reset
- Reduce `--workers` count
- Process in smaller batches

**Out of memory:**
- Reduce `--chunk_size`
- Process fewer files at once
- Close other applications

**Network errors:**
- Check internet connection
- Verify proxy settings
- Try with `--verbose` for details

## See Also

- [Usage Guide](usage/) - Detailed usage examples
- [Configuration](configuration/) - Configuration options
- [Examples](examples/) - Real-world examples
- [API Reference](api-reference/) - Python API documentation