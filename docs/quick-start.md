---
layout: default
title: Quick Start
nav_order: 2
parent: Usage Guide
---

# Quick Start Guide
{: .no_toc }

Get up and running with Cerebrate File in 5 minutes
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## 1. Install Cerebrate File

```bash
# Using pip
pip install cerebrate-file

# Using uv (faster)
uv pip install cerebrate-file
```

## 2. Set Your API Key

Get your API key from [cerebras.ai](https://cerebras.ai) and set it:

```bash
export CEREBRAS_API_KEY="csk-your-api-key-here"
```

## 3. Process Your First File

### Simple Processing

```bash
# Process a single file (overwrites original)
cerebrate-file document.md --prompt "Improve clarity and grammar"
```

### Save to New File

```bash
# Process and save to a new file
cerebrate-file input.md --output improved.md --prompt "Fix typos and improve flow"
```

## 4. Common Use Cases

### Summarize a Document

```bash
cerebrate-file report.md \
  --prompt "Summarize to 500 words with key points" \
  --output summary.md
```

### Improve Code Documentation

```bash
cerebrate-file script.py \
  --prompt "Add comprehensive docstrings and comments" \
  --data_format code \
  --output documented.py
```

### Translate Content

```bash
cerebrate-file article.md \
  --prompt "Translate to Spanish, keep formatting" \
  --output articulo.md
```

### Process Multiple Files

```bash
# Process all markdown files in current directory
cerebrate-file . \
  --recurse "*.md" \
  --prompt "Add table of contents" \
  --output ./processed/
```

## 5. Essential Options

### Chunking Options

```bash
# For large documents
cerebrate-file large_doc.md --chunk_size 48000

# For code files
cerebrate-file app.py --data_format code

# For articles
cerebrate-file article.txt --data_format semantic
```

### Model Parameters

```bash
# More creative output
cerebrate-file story.md --temp 0.9

# More consistent output
cerebrate-file technical.md --temp 0.3
```

### Debug and Test

```bash
# See what's happening
cerebrate-file doc.md --verbose

# Test without API calls
cerebrate-file doc.md --dry_run
```

## 6. Advanced Features

### Recursive Processing

Process entire directory trees:

```bash
# Process all Python files recursively
cerebrate-file ./src \
  --recurse "**/*.py" \
  --prompt "Add type hints" \
  --output ./typed/ \
  --workers 4
```

### Using Instruction Files

For complex instructions:

```bash
# Create instruction file
cat > instructions.md << EOF
1. Fix all grammar and spelling errors
2. Improve sentence structure
3. Add section summaries
4. Ensure consistent tone
EOF

# Use instruction file
cerebrate-file document.md \
  --file_prompt instructions.md \
  --output edited.md
```

### Parallel Processing

Speed up multiple files:

```bash
# Process with 8 parallel workers
cerebrate-file . \
  --recurse "**/*.md" \
  --workers 8 \
  --output ./processed/
```

## 7. Monitor Progress

The tool shows:
- 📊 Progress bar with percentage
- 📁 Current file being processed
- ✅ Files completed
- 🔄 Remaining API calls

## 8. Check Your Results

After processing:

```bash
# View the output
cat output.md

# Compare with original
diff input.md output.md

# Check remaining API calls
cerebrate-file small.txt --verbose | grep "Remaining"
```

## 9. Troubleshooting Quick Fixes

### API Key Not Found
```bash
echo 'CEREBRAS_API_KEY=csk-...' > .env
```

### Rate Limited
```bash
# Use fewer workers
cerebrate-file . --recurse "**/*.md" --workers 2
```

### File Too Large
```bash
# Use smaller chunks
cerebrate-file large.md --chunk_size 16000
```

### Out of Memory
```bash
# Process sequentially
cerebrate-file . --recurse "**/*.md" --workers 1
```

## 10. Next Steps

Now that you're up and running:

1. **Explore More Options**: See [CLI Reference](../cli-reference/)
2. **Learn Best Practices**: Read [Configuration Guide](../configuration/)
3. **See Examples**: Browse [Real-World Examples](../examples/)
4. **Troubleshoot Issues**: Check [Troubleshooting Guide](../troubleshooting/)

## Quick Reference Card

### Essential Commands

| Task | Command |
|------|---------|
| **Process file** | `cerebrate-file input.md` |
| **Save to new file** | `cerebrate-file input.md -o output.md` |
| **Add instructions** | `cerebrate-file doc.md -p "instructions"` |
| **Process directory** | `cerebrate-file . --recurse "*.md"` |
| **Test chunking** | `cerebrate-file doc.md --dry_run` |
| **Debug mode** | `cerebrate-file doc.md --verbose` |

### Key Parameters

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `--output` | Output path | `--output result.md` |
| `--prompt` | Instructions | `--prompt "Summarize"` |
| `--recurse` | Pattern | `--recurse "**/*.py"` |
| `--workers` | Parallel | `--workers 8` |
| `--chunk_size` | Chunk size | `--chunk_size 32000` |
| `--data_format` | Strategy | `--data_format code` |
| `--temp` | Temperature | `--temp 0.7` |
| `--verbose` | Debug info | `--verbose` |

### Chunking Strategies

| Format | Best For | Example |
|--------|----------|---------|
| `markdown` | Documents | README, docs |
| `code` | Source files | .py, .js, .java |
| `semantic` | Articles | Blog posts, essays |
| `text` | Plain text | CSV, logs, data |

## Getting Help

- **Help command**: `cerebrate-file --help`
- **Documentation**: [Full docs](https://twardoch.github.io/cerebrate-file/)
- **Issues**: [GitHub Issues](https://github.com/twardoch/cerebrate-file/issues)
- **Discussions**: [GitHub Discussions](https://github.com/twardoch/cerebrate-file/discussions)