---
layout: default
title: Troubleshooting
nav_order: 8
---

# Troubleshooting
{: .no_toc }

Solutions to common issues and error messages
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Common Issues

### API Key Issues

#### Error: CEREBRAS_API_KEY not found

**Symptom:**
```
Error: CEREBRAS_API_KEY environment variable not found
```

**Solutions:**

1. Set the environment variable:
   ```bash
   export CEREBRAS_API_KEY="csk-your-key-here"
   ```

2. Create a `.env` file:
   ```bash
   echo 'CEREBRAS_API_KEY=csk-your-key-here' > .env
   ```

3. Pass directly (not recommended):
   ```python
   process_document(input_data="file.md", api_key="csk-...")
   ```

#### Error: Invalid API Key Format

**Symptom:**
```
Warning: API key appears to be a placeholder
```

**Solution:**
- Ensure your API key starts with `csk-`
- Get a valid key from [cerebras.ai](https://cerebras.ai)
- Check for typos or extra spaces

### Rate Limiting

#### Error: Rate limit exceeded

**Symptom:**
```
RateLimitError: 429 Too Many Requests
```

**Solutions:**

1. **Wait for reset:**
   - Per-minute limits reset after 60 seconds
   - Daily limits reset at midnight UTC

2. **Reduce parallel workers:**
   ```bash
   cerebrate-file . --recurse "**/*.md" --workers 2
   ```

3. **Process in batches:**
   ```bash
   # Process 10 files at a time
   find . -name "*.md" | head -10 | xargs -I {} cerebrate-file {}
   ```

4. **Check remaining quota:**
   ```bash
   cerebrate-file small.txt --verbose | grep "Remaining"
   ```

### Token Limit Issues

#### Error: Context length exceeded

**Symptom:**
```
TokenLimitError: Maximum context length is 131072 tokens
```

**Solutions:**

1. **Reduce chunk size:**
   ```bash
   cerebrate-file large.md --chunk_size 24000
   ```

2. **Lower completion ratio:**
   ```bash
   cerebrate-file doc.md --max_tokens_ratio 50
   ```

3. **Reduce sample size:**
   ```bash
   cerebrate-file doc.md --sample_size 100
   ```

4. **Use simpler prompts:**
   - Shorter instructions use fewer tokens
   - Avoid redundant instructions

### File Processing Errors

#### Error: File not found

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory
```

**Solutions:**

1. **Check file path:**
   ```bash
   ls -la input.md
   pwd  # Verify current directory
   ```

2. **Use absolute paths:**
   ```bash
   cerebrate-file /full/path/to/file.md
   ```

3. **Check permissions:**
   ```bash
   ls -la file.md
   chmod 644 file.md  # If needed
   ```

#### Error: Permission denied

**Symptom:**
```
PermissionError: [Errno 13] Permission denied
```

**Solutions:**

1. **Check file permissions:**
   ```bash
   chmod 644 input.md  # Read permission
   chmod 755 output_dir/  # Directory access
   ```

2. **Check output directory:**
   ```bash
   mkdir -p output
   chmod 755 output
   ```

3. **Run with appropriate user:**
   ```bash
   sudo chown $USER:$USER file.md
   ```

### Network Issues

#### Error: Connection timeout

**Symptom:**
```
NetworkError: HTTPSConnectionPool timeout
```

**Solutions:**

1. **Check internet connection:**
   ```bash
   ping api.cerebras.ai
   curl https://api.cerebras.ai
   ```

2. **Configure proxy if needed:**
   ```bash
   export HTTPS_PROXY="http://proxy:8080"
   ```

3. **Increase timeout (in code):**
   ```python
   client = CerebrasClient(api_key, timeout=60)
   ```

4. **Retry with verbose mode:**
   ```bash
   cerebrate-file doc.md --verbose
   ```

### Chunking Issues

#### Error: No chunks created

**Symptom:**
```
ValueError: No chunks were created from the input
```

**Solutions:**

1. **Check file content:**
   ```bash
   wc -l input.md  # Check if file has content
   file input.md    # Check file type
   ```

2. **Try different format:**
   ```bash
   cerebrate-file doc.md --data_format text
   ```

3. **Check encoding:**
   ```bash
   file -bi input.md  # Check encoding
   iconv -f ISO-8859-1 -t UTF-8 input.md > input_utf8.md
   ```

#### Error: Chunks too large

**Symptom:**
```
Chunk size exceeds maximum token limit
```

**Solution:**
```bash
cerebrate-file doc.md --chunk_size 16000
```

### Output Issues

#### Problem: Output is truncated

**Solutions:**

1. **Increase token ratio:**
   ```bash
   cerebrate-file doc.md --max_tokens_ratio 150
   ```

2. **Check for rate limiting:**
   - Look for incomplete responses
   - Add `--verbose` to see details

3. **Process smaller chunks:**
   ```bash
   cerebrate-file doc.md --chunk_size 24000
   ```

#### Problem: Output formatting is broken

**Solutions:**

1. **Use appropriate format:**
   ```bash
   cerebrate-file doc.md --data_format markdown
   ```

2. **Preserve frontmatter:**
   ```bash
   cerebrate-file doc.md --explain
   ```

3. **Check prompt instructions:**
   - Ensure prompt doesn't conflict with format
   - Test with simpler prompts first

### Recursive Processing Issues

#### Error: Invalid glob pattern

**Symptom:**
```
ValueError: Invalid pattern: **/*.{md,txt}
```

**Solutions:**

1. **Quote the pattern:**
   ```bash
   cerebrate-file . --recurse "**/*.{md,txt}"
   ```

2. **Use simpler patterns:**
   ```bash
   cerebrate-file . --recurse "**/*.md"
   ```

3. **Test pattern first:**
   ```bash
   find . -name "*.md"  # Verify files exist
   ```

#### Problem: Not finding files

**Solutions:**

1. **Check current directory:**
   ```bash
   pwd
   ls -la
   ```

2. **Use correct pattern:**
   ```bash
   # Current directory only
   --recurse "*.md"

   # All subdirectories
   --recurse "**/*.md"

   # Specific directory
   --recurse "docs/**/*.md"
   ```

3. **Check file extensions:**
   ```bash
   find . -type f | head -20
   ```

### Performance Issues

#### Problem: Processing is very slow

**Solutions:**

1. **Increase workers:**
   ```bash
   cerebrate-file . --recurse "**/*.md" --workers 8
   ```

2. **Use larger chunks:**
   ```bash
   cerebrate-file doc.md --chunk_size 48000
   ```

3. **Reduce sample size:**
   ```bash
   cerebrate-file doc.md --sample_size 100
   ```

4. **Check system resources:**
   ```bash
   top  # Check CPU and memory
   df -h  # Check disk space
   ```

#### Problem: High memory usage

**Solutions:**

1. **Process sequentially:**
   ```bash
   cerebrate-file . --recurse "**/*.md" --workers 1
   ```

2. **Smaller chunks:**
   ```bash
   cerebrate-file large.md --chunk_size 16000
   ```

3. **Process in batches:**
   ```bash
   for file in *.md; do
     cerebrate-file "$file"
     sleep 1  # Brief pause
   done
   ```

## Error Messages Reference

### API Errors

| Error Code | Meaning | Solution |
|------------|---------|----------|
| 400 | Bad Request | Check prompt and parameters |
| 401 | Unauthorized | Verify API key |
| 403 | Forbidden | Check API key permissions |
| 429 | Rate Limited | Wait and retry |
| 500 | Server Error | Retry later |
| 503 | Service Unavailable | API maintenance, retry later |

### Exit Codes

| Code | Meaning | Typical Cause |
|------|---------|---------------|
| 0 | Success | Normal completion |
| 1 | General Error | Various issues |
| 2 | Invalid Arguments | Bad CLI parameters |
| 3 | API Key Not Found | Missing CEREBRAS_API_KEY |
| 4 | File Not Found | Input file doesn't exist |
| 5 | Permission Denied | File access issues |
| 6 | API Error | Cerebras API problem |
| 7 | Rate Limit | Too many requests |
| 8 | Network Error | Connection issues |

## Debugging Techniques

### Enable Verbose Logging

```bash
# Maximum debugging information
cerebrate-file doc.md --verbose

# Save logs to file
cerebrate-file doc.md --verbose 2> debug.log

# Separate stdout and stderr
cerebrate-file doc.md --verbose \
  1> output.txt \
  2> errors.log
```

### Test with Dry Run

```bash
# Test chunking without API calls
cerebrate-file large.md --dry_run --verbose

# Check what would be processed
cerebrate-file . --recurse "**/*.md" --dry_run
```

### Validate Environment

```bash
# Check API key
echo $CEREBRAS_API_KEY | head -c 10

# Test API connection
curl -H "Authorization: Bearer $CEREBRAS_API_KEY" \
  https://api.cerebras.ai/v1/models

# Check Python version
python --version

# Check package version
python -c "import cerebrate_file; print(cerebrate_file.__version__)"
```

### Monitor Processing

```bash
# Watch progress
cerebrate-file doc.md --verbose | tee process.log

# Monitor system resources
watch -n 1 'ps aux | grep cerebrate'

# Check output files
watch -n 2 'ls -la output/'
```

## Getting Help

### Resources

1. **Documentation**: [Full documentation](https://twardoch.github.io/cerebrate-file/)
2. **GitHub Issues**: [Report bugs](https://github.com/twardoch/cerebrate-file/issues)
3. **Discussions**: [Ask questions](https://github.com/twardoch/cerebrate-file/discussions)

### Reporting Issues

When reporting issues, include:

1. **Error message**: Complete error output
2. **Command**: Exact command used
3. **Environment**:
   ```bash
   cerebrate-file --version
   python --version
   echo $CEREBRAS_API_KEY | head -c 10
   ```
4. **File sample**: Small reproducing example
5. **Verbose output**: Run with `--verbose`

### Support Checklist

Before requesting help:

- [ ] Check this troubleshooting guide
- [ ] Update to latest version
- [ ] Test with a small file
- [ ] Try with `--verbose` flag
- [ ] Check API key is valid
- [ ] Verify file permissions
- [ ] Test network connection
- [ ] Review error message carefully

## FAQ

### General Questions

**Q: How much does it cost?**
A: Cerebras offers free tier with daily limits. Check [cerebras.ai](https://cerebras.ai) for pricing.

**Q: What file types are supported?**
A: Any text file. Binary files need conversion to text first.

**Q: What's the maximum file size?**
A: No hard limit, but very large files may take long to process.

**Q: Can I process PDFs?**
A: Convert PDF to text first using tools like `pdftotext`.

### Technical Questions

**Q: Why is processing slow?**
A: Large files, small chunks, or rate limiting. Try increasing chunk size and workers.

**Q: How do I process code files?**
A: Use `--data_format code` for better code-aware chunking.

**Q: Can I use multiple API keys?**
A: Not simultaneously. Process different batches with different keys.

**Q: Does it work offline?**
A: No, requires internet connection to Cerebras API.

### Best Practices

**Q: What's the optimal chunk size?**
A: 32,000-48,000 tokens for most content. Smaller for code.

**Q: How many workers should I use?**
A: 4-8 workers typically optimal. Depends on system and rate limits.

**Q: Should I use streaming?**
A: Yes (default). Provides better progress feedback.

**Q: How do I preserve formatting?**
A: Use appropriate `--data_format` for your content type.

## Next Steps

- Review [Configuration](configuration/) for optimization
- See [Examples](examples/) for working solutions
- Check [API Reference](api-reference/) for programmatic use
- Explore [CLI Reference](cli-reference/) for all options