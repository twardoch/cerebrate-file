---
layout: default
title: Usage Guide
nav_order: 3
---

# Usage Guide
{: .no_toc }

Comprehensive guide to using Cerebrate File effectively
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Basic Usage

### Processing a Single File

The simplest use case is processing a single document:

```bash
cerebrate-file input.md
```

This will process `input.md` and overwrite it with the AI-processed result.

### Specifying Output File

To save the result to a different file:

```bash
cerebrate-file input.md --output output.md
```

### Adding Instructions

Provide instructions to guide the AI processing:

```bash
cerebrate-file document.md \
  --prompt "Summarize each section to 2-3 sentences"
```

### Using Instruction Files

For complex instructions, use a separate file:

```bash
cerebrate-file report.md \
  --file_prompt instructions.md \
  --output summary.md
```

## Advanced Features

### Recursive Processing

Process multiple files matching a pattern:

```bash
# Process all markdown files recursively
cerebrate-file . --output ./processed --recurse "**/*.md"

# Process specific file types
cerebrate-file ./src --output ./docs --recurse "**/*.{py,js,ts}"

# Process with specific depth
cerebrate-file . --output ./output --recurse "*.txt"  # Current directory only
cerebrate-file . --output ./output --recurse "*/*.txt"  # One level deep
```

### Parallel Processing

Speed up processing of multiple files:

```bash
# Use 8 workers for parallel processing
cerebrate-file . --output ./output --recurse "**/*.md" --workers 8

# Automatic worker count (based on CPU cores)
cerebrate-file . --output ./output --recurse "**/*.md" --workers 0
```

### Chunking Strategies

Choose the best chunking strategy for your content:

```bash
# Markdown-aware chunking (default)
cerebrate-file doc.md --data_format markdown

# Code-aware chunking for source files
cerebrate-file script.py --data_format code

# Semantic chunking for natural text
cerebrate-file article.txt --data_format semantic

# Simple text chunking
cerebrate-file data.txt --data_format text
```

### Chunk Size Control

Optimize chunk sizes for your use case:

```bash
# Smaller chunks for detailed processing
cerebrate-file large.md --chunk_size 16000

# Larger chunks for context preservation
cerebrate-file report.md --chunk_size 64000

# Adjust completion budget
cerebrate-file doc.md --max_tokens_ratio 50  # Use 50% of chunk size for output
```

### Context Preservation

Control how context is maintained between chunks:

```bash
# Increase overlap for better continuity
cerebrate-file novel.md --sample_size 500

# Minimal overlap for independent sections
cerebrate-file data.csv --sample_size 50
```

## Working with Different File Types

### Markdown Documents

```bash
cerebrate-file README.md \
  --prompt "Add emojis to section headers" \
  --data_format markdown
```

### Source Code

```bash
cerebrate-file app.py \
  --prompt "Add comprehensive docstrings" \
  --data_format code \
  --chunk_size 24000
```

### Plain Text

```bash
cerebrate-file article.txt \
  --prompt "Fix grammar and improve clarity" \
  --data_format text
```

### Mixed Content

```bash
# Process multiple file types with appropriate strategies
cerebrate-file . --output ./processed \
  --recurse "**/*.{md,py,txt}" \
  --prompt "Improve documentation and code comments"
```

## Metadata Processing

### Extracting Metadata

Use `--explain` mode to extract document metadata:

```bash
cerebrate-file blog_post.md --explain
```

This extracts/generates:
- Title
- Author
- Document ID
- Type classification
- Date

### Preserving Frontmatter

Frontmatter in markdown files is automatically preserved:

```yaml
---
title: My Document
author: John Doe
---
# Content here...
```

## Model Parameters

### Temperature Control

Adjust creativity vs consistency:

```bash
# More creative/varied output
cerebrate-file story.md --temp 0.9

# More consistent/deterministic output
cerebrate-file technical.md --temp 0.3
```

### Top-p Sampling

Control token selection diversity:

```bash
# More diverse vocabulary
cerebrate-file creative.md --top_p 0.95

# More focused vocabulary
cerebrate-file formal.md --top_p 0.7
```

## Monitoring and Debugging

### Verbose Mode

See detailed processing information:

```bash
cerebrate-file large.md --verbose
```

Shows:
- Chunk boundaries and sizes
- Token counts
- API requests and responses
- Rate limit status
- Processing time

### Dry Run

Test chunking without API calls:

```bash
cerebrate-file huge.md --dry_run --verbose
```

Useful for:
- Checking chunk sizes
- Validating token budgets
- Testing patterns
- Debugging issues

### Progress Display

The rich terminal UI shows:
- Current file being processed
- Progress bar with percentage
- Output file path
- Remaining API calls

## Best Practices

### 1. Choose Appropriate Chunk Sizes

- **Small files (<10K tokens)**: Use default 32K chunks
- **Large files (>100K tokens)**: Consider 48K-64K chunks
- **Code files**: Use 24K chunks for better function boundaries

### 2. Select Right Chunking Strategy

- **Markdown**: Use `markdown` format for documents
- **Code**: Use `code` format for source files
- **Articles**: Use `semantic` format for natural text
- **Data**: Use `text` format for structured data

### 3. Optimize for Rate Limits

- Monitor remaining requests: `📊 Remaining today: X requests`
- Use `--workers` wisely for parallel processing
- Add delays between batches if needed

### 4. Handle Large Projects

```bash
# Process in batches
find . -name "*.md" -print0 | \
  xargs -0 -n 10 cerebrate-file --output ./processed

# Or use parallel with controlled concurrency
cerebrate-file . --output ./output \
  --recurse "**/*.md" \
  --workers 4
```

### 5. Preserve Context

For documents requiring strong continuity:
```bash
cerebrate-file book.md \
  --sample_size 500 \
  --chunk_size 48000 \
  --prompt "Maintain narrative voice and continuity"
```

## Common Workflows

### Document Translation

```bash
cerebrate-file document.md \
  --prompt "Translate to Spanish, preserve formatting" \
  --output documento.md
```

### Code Documentation

```bash
cerebrate-file ./src \
  --recurse "**/*.py" \
  --prompt "Add comprehensive docstrings following Google style" \
  --output ./documented
```

### Content Summarization

```bash
cerebrate-file reports/ \
  --recurse "*.pdf.txt" \
  --prompt "Create executive summary, max 500 words" \
  --output summaries/
```

### Style Transformation

```bash
cerebrate-file blog.md \
  --file_prompt style_guide.md \
  --prompt "Rewrite in professional tone" \
  --output blog_professional.md
```

### Batch Processing

```bash
# Process all markdown files with consistent instructions
for file in *.md; do
  cerebrate-file "$file" \
    --file_prompt instructions.md \
    --output "processed/${file}"
done
```

## Error Handling

### Rate Limit Handling

Cerebrate File automatically handles rate limits:
- Exponential backoff for rate limit errors
- Automatic retry with delays
- Clear status messages

### Network Issues

For unreliable connections:
```bash
# Increase retry attempts (handled automatically)
cerebrate-file document.md --verbose
```

### Large File Issues

For very large files:
```bash
# Use smaller chunks and lower completion ratio
cerebrate-file huge.md \
  --chunk_size 24000 \
  --max_tokens_ratio 50
```

## Tips and Tricks

### 1. Preview Changes

Use dry run to preview:
```bash
cerebrate-file doc.md --dry_run --verbose
```

### 2. Save Prompts

Create reusable instruction files:
```bash
echo "Your instructions here" > prompts/summarize.md
cerebrate-file doc.md --file_prompt prompts/summarize.md
```

### 3. Chain Processing

Process files through multiple stages:
```bash
# Stage 1: Translate
cerebrate-file doc.md --prompt "Translate to Spanish" --output doc_es.md

# Stage 2: Summarize
cerebrate-file doc_es.md --prompt "Summarize key points" --output summary_es.md
```

### 4. Use Shell Features

Leverage shell capabilities:
```bash
# Process files modified today
find . -name "*.md" -mtime -1 -exec cerebrate-file {} \;

# Process with confirmation
for file in *.txt; do
  read -p "Process $file? " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    cerebrate-file "$file"
  fi
done
```

## Next Steps

- Explore [CLI Reference](cli-reference/) for all options
- See [Examples](examples/) for real-world use cases
- Check [Troubleshooting](troubleshooting/) for common issues
- Learn about [API Reference](api-reference/) for programmatic use