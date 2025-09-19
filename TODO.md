---
this_file: TODO.md
---

## Simple Quality Improvements - Version 1.3.0

### 1. Add Simple Progress Counter
- [ ] Show "Processing chunk X of Y..." for each chunk in non-verbose mode
- [ ] Keep existing progress bar, just add chunk counter above it
- [ ] Simple format: "📝 Processing chunk 3 of 7..."

### 2. Support Reading Prompt from stdin
- [ ] Allow file_prompt="-" to read prompt from stdin
- [ ] Useful for piping prompts: echo "Summarize this" | python cereproc.py input.txt output.txt -
- [ ] Simple implementation using sys.stdin.read()

### 3. Show File Size Summary
- [ ] After completion, show input vs output file sizes
- [ ] Format: "📊 Input: 245 KB → Output: 89 KB (36% of original)"
- [ ] Helps users understand compression/expansion from processing

## Rationale
These improvements are:
- **Simple**: Each can be implemented in <10 lines of code
- **Practical**: Add real value to user experience
- **Non-invasive**: Don't change core functionality