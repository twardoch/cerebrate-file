---
layout: default
title: Usage Guide
nav_order: 3
---

# Usage Guide
{: .no_toc }

How to use Cerebrate File effectively
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Basic Usage

### Processing a Single File

The simplest way to use Cerebrate File is on one document:

```bash
cerebrate-file input.md
```

This overwrites `input.md` with the processed version.

### Specifying Output File

To save the result elsewhere:

```bash
cerebrate-file input.md --output output.md
```

### Adding Instructions

Add instructions for the AI:

```bash
cerebrate-file document.md \
  --prompt "Summarize each section in 2-3 sentences"
```

### Using Instruction Files

For longer or reusable instructions, use a file:

```bash
cerebrate-file report.md \
  --file_prompt instructions.md \
  --output summary.md
```

## Advanced Features

### Recursive Processing

Process multiple files by pattern:

```bash
# All markdown files, recursively
cerebrate-file . --output ./processed --recurse "**/*.md"

# Specific file types
cerebrate-file ./src --output ./docs --recurse "**/*.{py,js,ts}"

# Limit depth
cerebrate-file . --output ./output --recurse "*.txt"      # Current dir only
cerebrate-file . --output ./output --recurse "*/*.txt"     # One level deep
```

### Parallel Processing

Speed up processing with multiple workers:

```bash
# Use 8 workers
cerebrate-file . --output ./output --recurse "**/*.md" --workers 8

# Auto-detect based on CPU cores
cerebrate-file . --output ./output --recurse "**/*.md" --workers 0
```

### Chunking Strategies

Choose the right strategy for your content:

```bash
# Markdown-aware (default)
cerebrate-file doc.md --data_format markdown

# Code-aware for source files
cerebrate-file script.py --data_format code

# Semantic chunking for natural text
cerebrate-file article.txt --data_format semantic

# Plain text
cerebrate-file data.txt --data_format text
```

### Chunk Size Control

Adjust chunk sizes:

```bash
# Smaller chunks = more detail
cerebrate-file large.md --chunk_size 16000

# Larger chunks = more context
cerebrate-file report.md --chunk_size 64000

# Control output size
cerebrate-file doc.md --max_tokens_ratio 50  # Output uses 50% of chunk size
```

### Context Preservation

Control overlap between chunks:

```bash
# More overlap = better continuity
cerebrate-file novel.md --sample_size 500

# Less overlap = faster processing
cerebrate-file data.csv --sample_size 50
```

## Working with Different File Types

### Markdown Documents

```bash
cerebrate-file README.md \
  --prompt "Add emojis to headers" \
  --data_format markdown
```

### Source Code

```bash
cerebrate-file app.py \
  --prompt "Add docstrings" \
  --data_format code \
  --chunk_size 24000
```

### Plain Text

```bash
cerebrate-file article.txt \
  --prompt "Fix grammar and clarify language" \
  --data_format text
```

### Mixed Content

```bash
# Process multiple file types at once
cerebrate-file . --output ./processed \
  --recurse "**/*.{md,py,txt}" \
  --prompt "Improve docs and comments"
```

## Metadata Processing

### Extracting Metadata

Use `--explain` to extract/generate metadata:

```bash
cerebrate-file blog_post.md --explain
```

Extracts:
- Title
- Author
- Document ID
- Type
- Date

### Preserving Frontmatter

Markdown frontmatter is preserved automatically:

```yaml
---
title: My Document
author: John Doe
---
# Content starts here...
```

## Model Parameters

### Temperature Control

Control creativity:

```bash
# High = more creative
cerebrate-file story.md --temp 0.9

# Low = more predictable
cerebrate-file technical.md --temp 0.3
```

### Top-p Sampling

Control vocabulary diversity:

```bash
# Wider range of words
cerebrate-file creative.md --top_p 0.95

# Stick to common words
cerebrate-file formal.md --top_p 0.7
```

## Monitoring and Debugging

### Verbose Mode

See what’s happening:

```bash
cerebrate-file large.md --verbose
```

Displays:
- Chunk boundaries
- Token usage
- API requests/responses
- Rate limits
- Timing info

### Dry Run

Test chunking without calling the API:

```bash
cerebrate-file huge.md --dry_run --verbose
```

Useful for:
- Checking chunk sizes
- Validating token limits
- Testing file patterns
- Debugging

### Progress Display

The terminal shows:
- Current file
- Progress percentage
- Output path
- Remaining API calls

## Best Practices

### 1. Chunk Sizes

- **Small files (<10K tokens)**: Default 32K chunks work fine
- **Large files (>100K tokens)**: Try 48K–64K chunks
- **Code files**: 24K chunks help keep functions intact

### 2. Chunking Strategy

- **Markdown**: Use `markdown`
- **Code**: Use `code`
- **Articles**: Use `semantic`
- **Structured data**: Use `text`

### 3. Rate Limits

- Watch remaining requests: `📊 Remaining today: X`
- Use `--workers` carefully
- Add delays if hitting limits

### 4. Large Projects

Process in controlled batches:

```bash
# Shell-based batching
find . -name "*.md" -print0 | \
  xargs -0 -n 10 cerebrate-file --output ./processed

# Or with limited parallelism
cerebrate-file . --output ./output \
  --recurse "**/*.md" \
  --workers 4
```

### 5. Preserve Context

For continuous text:

```bash
cerebrate-file book.md \
  --sample_size 500 \
  --chunk_size 48000 \
  --prompt "Keep narrative voice consistent"
```

## Common Workflows

### Document Translation

```bash
cerebrate-file document.md \
  --prompt "Translate to Spanish, keep formatting" \
  --output documento.md
```

### Code Documentation

```bash
cerebrate-file ./src \
  --recurse "**/*.py" \
  --prompt "Add Google-style docstrings" \
  --output ./documented
```

### Content Summarization

```bash
cerebrate-file reports/ \
  --recurse "*.pdf.txt" \
  --prompt "Executive summary, 500 words max" \
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
# Apply same instructions to all markdown files
for file in *.md; do
  cerebrate-file "$file" \
    --file_prompt instructions.md \
    --output "processed/${file}"
done
```

## Error Handling

### Rate Limits

Cerebrate File handles them automatically:
- Exponential backoff
- Retries with delays
- Clear status updates

### Network Issues

For flaky connections:

```bash
# Verbose mode helps debug retries
cerebrate-file document.md --verbose
```

### Large Files

If you hit token limits:

```bash
# Reduce chunk size and output ratio
cerebrate-file huge.md \
  --chunk_size 24000 \
  --max_tokens_ratio 50
```

## Tips and Tricks

### 1. Preview Changes

Dry run before processing:

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

Multi-step workflows:

```bash
# Step 1: Translate
cerebrate-file doc.md --prompt "Translate to Spanish" --output doc_es.md

# Step 2: Summarize
cerebrate-file doc_es.md --prompt "Summarize key points" --output summary_es.md
```

### 4. Use Shell Features

Leverage shell tools:

```bash
# Process files modified today
find . -name "*.md" -mtime -1 -exec cerebrate-file {} \;

# Confirm before processing
for file in *.txt; do
  read -p "Process $file? " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    cerebrate-file "$file"
  fi
done
```

## Next Steps

- [CLI Reference](cli-reference/) – full list of options
- [Examples](examples/) – real-world use cases
- [Troubleshooting](troubleshooting/) – common issues
- [API Reference](api-reference/) – programmatic usage