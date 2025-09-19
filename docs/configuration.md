---
layout: default
title: Configuration
nav_order: 5
---

# Configuration
{: .no_toc }

Configure Cerebrate File for optimal performance
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Environment Configuration

### API Key Setup

The Cerebras API key is the only required configuration:

```bash
# Option 1: Environment variable
export CEREBRAS_API_KEY="csk-your-api-key-here"

# Option 2: .env file
echo 'CEREBRAS_API_KEY=csk-your-api-key-here' > .env

# Option 3: Shell configuration file
echo 'export CEREBRAS_API_KEY="csk-your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### Security Best Practices

1. **Never commit API keys**:
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   echo "*.key" >> .gitignore
   ```

2. **Use secure storage**:
   ```bash
   # macOS Keychain
   security add-generic-password -a "$USER" -s "CEREBRAS_API_KEY" -w "csk-..."

   # Linux Secret Service
   secret-tool store --label="Cerebras API Key" api cerebras
   ```

3. **Restrict file permissions**:
   ```bash
   chmod 600 .env
   ```

## Chunking Configuration

### Optimal Chunk Sizes by Content Type

| Content Type | Recommended Size | Sample Size | Format |
|-------------|-----------------|-------------|---------|
| **Documentation** | 32,000 | 200 | markdown |
| **Source Code** | 24,000 | 300 | code |
| **Articles** | 48,000 | 400 | semantic |
| **Data/CSV** | 16,000 | 100 | text |
| **Books/Novels** | 64,000 | 500 | semantic |

### Chunking Strategy Selection

```bash
# Documentation with structure preservation
cerebrate-file docs.md \
  --data_format markdown \
  --chunk_size 32000 \
  --sample_size 200

# Code with function boundaries
cerebrate-file app.py \
  --data_format code \
  --chunk_size 24000 \
  --sample_size 300

# Natural text with semantic breaks
cerebrate-file article.txt \
  --data_format semantic \
  --chunk_size 48000 \
  --sample_size 400
```

## Model Parameters

### Temperature Guidelines

| Use Case | Temperature | Description |
|----------|------------|-------------|
| **Technical Documentation** | 0.3 | High consistency, minimal variation |
| **Code Generation** | 0.4 | Reliable, predictable output |
| **General Content** | 0.7 | Balanced creativity and coherence |
| **Creative Writing** | 0.9 | Maximum creativity and variety |
| **Translations** | 0.5 | Accurate with some flexibility |

### Top-p Recommendations

| Use Case | Top-p | Effect |
|----------|-------|--------|
| **Formal Writing** | 0.7 | Focused vocabulary |
| **Technical Content** | 0.75 | Balanced selection |
| **General Purpose** | 0.8 | Default setting |
| **Creative Content** | 0.95 | Diverse vocabulary |

### Combined Settings Examples

```bash
# Technical documentation
cerebrate-file manual.md \
  --temp 0.3 \
  --top_p 0.7 \
  --prompt "Improve clarity and accuracy"

# Creative rewriting
cerebrate-file story.md \
  --temp 0.9 \
  --top_p 0.95 \
  --prompt "Make it more engaging"

# Code documentation
cerebrate-file src/main.py \
  --temp 0.4 \
  --top_p 0.75 \
  --prompt "Add comprehensive docstrings"
```

## Performance Optimization

### Worker Configuration

Optimal worker counts for different scenarios:

```bash
# CPU-bound (many small files)
cerebrate-file . --recurse "**/*.md" --workers 8

# I/O-bound (few large files)
cerebrate-file . --recurse "**/*.pdf.txt" --workers 4

# Memory-constrained systems
cerebrate-file . --recurse "**/*" --workers 2

# Auto-detect optimal count
cerebrate-file . --recurse "**/*.py" --workers 0
```

### Memory Management

For systems with limited memory:

```bash
# Reduce memory usage
cerebrate-file large.md \
  --chunk_size 16000 \
  --workers 2 \
  --max_tokens_ratio 50

# Process files sequentially
cerebrate-file . \
  --recurse "**/*.txt" \
  --workers 1
```

### Network Optimization

For slow or unreliable connections:

```bash
# Smaller chunks for faster requests
cerebrate-file doc.md \
  --chunk_size 16000 \
  --verbose  # Monitor progress

# Use proxy if available
export HTTPS_PROXY="http://proxy:8080"
cerebrate-file doc.md
```

## File Organization

### Project Structure

Recommended directory structure:

```
project/
├── input/              # Original files
│   ├── docs/
│   ├── src/
│   └── data/
├── output/             # Processed files
│   ├── docs/
│   ├── src/
│   └── data/
├── prompts/            # Reusable instruction files
│   ├── summarize.md
│   ├── translate_es.md
│   └── add_comments.md
├── .env                # API key (git-ignored)
└── .gitignore
```

### Prompt Library

Create reusable instruction files:

```bash
# Create prompt library
mkdir prompts

# Save common instructions
cat > prompts/summarize.md << 'EOF'
Create a concise summary following these guidelines:
- Maximum 500 words
- Bullet points for key concepts
- Preserve technical accuracy
- Include main conclusions
EOF

# Use saved prompts
cerebrate-file report.md \
  --file_prompt prompts/summarize.md \
  --output summaries/report.md
```

## Batch Processing Configuration

### Shell Scripts

Create processing scripts for common tasks:

```bash
#!/bin/bash
# process_docs.sh

# Configuration
INPUT_DIR="./docs"
OUTPUT_DIR="./processed"
PROMPT_FILE="./prompts/improve.md"
WORKERS=4

# Process all markdown files
cerebrate-file "$INPUT_DIR" \
  --output "$OUTPUT_DIR" \
  --recurse "**/*.md" \
  --file_prompt "$PROMPT_FILE" \
  --workers "$WORKERS" \
  --chunk_size 32000 \
  --temp 0.5
```

### Makefiles

Use Make for complex workflows:

```makefile
# Makefile

.PHONY: docs code all clean

# Variables
OUTPUT_DIR = processed
WORKERS = 4

# Process documentation
docs:
	cerebrate-file ./docs \
		--output $(OUTPUT_DIR)/docs \
		--recurse "**/*.md" \
		--file_prompt prompts/doc_style.md \
		--workers $(WORKERS)

# Process code
code:
	cerebrate-file ./src \
		--output $(OUTPUT_DIR)/src \
		--recurse "**/*.py" \
		--prompt "Add type hints and docstrings" \
		--data_format code \
		--workers $(WORKERS)

# Process everything
all: docs code

# Clean output
clean:
	rm -rf $(OUTPUT_DIR)
```

## Advanced Configuration

### Custom Aliases

Add to your shell configuration:

```bash
# ~/.bashrc or ~/.zshrc

# Alias for common operations
alias cf='cerebrate-file'
alias cf-docs='cerebrate-file --data_format markdown --chunk_size 32000'
alias cf-code='cerebrate-file --data_format code --chunk_size 24000'
alias cf-dry='cerebrate-file --dry_run --verbose'

# Function for recursive processing
cf-recursive() {
    cerebrate-file . \
        --output ./processed \
        --recurse "$1" \
        --workers 4 \
        "${@:2}"
}
```

### Configuration File (Future Feature)

Planned support for configuration files:

```yaml
# .cerebrate.yml (planned)
defaults:
  chunk_size: 32000
  sample_size: 200
  workers: 4
  temp: 0.7
  top_p: 0.8

profiles:
  documentation:
    data_format: markdown
    chunk_size: 32000
    temp: 0.5

  code:
    data_format: code
    chunk_size: 24000
    temp: 0.4

  creative:
    data_format: semantic
    temp: 0.9
    top_p: 0.95
```

## Monitoring and Logging

### Verbose Output

Configure logging levels:

```bash
# Maximum verbosity
cerebrate-file doc.md --verbose

# Redirect logs to file
cerebrate-file doc.md --verbose 2> process.log

# Separate stdout and stderr
cerebrate-file doc.md --verbose \
  1> output.txt \
  2> errors.log
```

### Progress Monitoring

Track processing progress:

```bash
# Watch output directory
watch -n 1 'ls -la ./output | tail -10'

# Monitor API calls
cerebrate-file doc.md --verbose | grep "Rate limit"

# Count processed files
find ./output -type f | wc -l
```

## Rate Limit Management

### Daily Planning

Calculate your daily capacity:

- **Daily limit**: 1000 requests
- **Average chunks per file**: ~5-10
- **Files per day**: ~100-200

### Strategies for High Volume

```bash
# Process in batches
find . -name "*.md" | head -100 | xargs -I {} \
  cerebrate-file {} --output processed/{}

# Add delays between batches
for batch in batch1 batch2 batch3; do
  cerebrate-file $batch --recurse "*.txt"
  sleep 300  # 5-minute delay
done

# Split across multiple days
cerebrate-file . --recurse "**/*.md[a-m]*"  # Day 1
cerebrate-file . --recurse "**/*.md[n-z]*"  # Day 2
```

## Troubleshooting Configuration

### Debug Mode

Enable maximum debugging:

```bash
# Set environment variables
export CEREBRATE_DEBUG=1
export LOGURU_LEVEL=DEBUG

# Run with verbose output
cerebrate-file test.md \
  --verbose \
  --dry_run
```

### Testing Configuration

Verify your setup:

```bash
# Test API connection
echo "test" | cerebrate-file - --prompt "Reply with 'OK'"

# Test chunking
cerebrate-file sample.md --dry_run --verbose

# Test rate limits
cerebrate-file small.txt --verbose | grep "Remaining"
```

## Best Practices Summary

1. **Always use appropriate chunk sizes** for your content type
2. **Set temperature based on desired consistency**
3. **Organize prompts in reusable files**
4. **Monitor rate limits** to avoid disruption
5. **Use workers wisely** based on system resources
6. **Create scripts** for repeated workflows
7. **Keep API keys secure** and never commit them
8. **Test with dry runs** before processing large batches

## Next Steps

- Review [CLI Reference](cli-reference/) for all options
- Explore [Examples](examples/) for specific use cases
- Check [Troubleshooting](troubleshooting/) for common issues
- See [API Reference](api-reference/) for programmatic access