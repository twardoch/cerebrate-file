---
this_file: PLAN.md
---

# cereproc.py - Project Plan

## Current Status
Version 1.2.1 - Document processing tool with advanced chunking and metadata handling

## Active Development - Version 1.3.0

### Quality Improvement 1: Chunk Overlap
**Objective**: Improve output coherence by maintaining context between chunks

**Technical Design**:
- Add `--overlap` CLI parameter (integer, 0-500 tokens, default: 100)
- When processing chunk N+1, extract last `overlap` tokens from chunk N
- Prepend overlap text to chunk N+1 with delimiter: `[Previous context: ...]`
- Adjust token budget calculations to account for overlap overhead
- Ensure overlap doesn't exceed 10% of chunk_size to maintain efficiency

**Implementation Steps**:
1. Add overlap parameter to CLI with validation
2. Modify chunk processing loop to track previous chunk's tail
3. Update prepare_chunk_messages to include overlap context
4. Adjust token counting to include overlap tokens
5. Test with various document types and overlap sizes

### Quality Improvement 2: Output Verification
**Objective**: Ensure data integrity and detect corruption/truncation

**Technical Design**:
- Use hashlib.sha256 for checksumming
- Calculate checksum of final output content before writing
- Display checksum in console output
- Save checksum to `{output_file}.sha256` for later verification
- Verify written file size matches expected length
- Basic structure check: ensure output isn't truncated mid-sentence

**Implementation Steps**:
1. Add checksum calculation after output assembly
2. Implement file size verification post-write
3. Create checksum sidecar file writer
4. Add structure validation (check for common truncation patterns)
5. Display verification results in output summary

### Quality Improvement 3: Enhanced Retry Logic
**Objective**: Improve resilience to transient API failures

**Technical Design**:
- Implement exponential backoff: delay = min(base * (2^attempt) + jitter, max_delay)
- Jitter = random.uniform(0, base_delay)
- Add `--max-retries` parameter (default: 3, range: 1-10)
- Add `--max-retry-delay` parameter (default: 60, range: 10-300 seconds)
- Track retry statistics: attempts per chunk, total retries, retry reasons
- Use tenacity library's built-in jitter support if available

**Implementation Steps**:
1. Add retry configuration parameters to CLI
2. Enhance retry logic with jitter calculation
3. Implement retry statistics tracking
4. Add detailed retry logging with reasons
5. Display retry summary in final statistics

## Completed Features
- Full --explain metadata processing with frontmatter support
- Code-aware chunking that respects programming structures
- Dry-run mode for testing without API calls
- Enhanced input validation with user-friendly error messages
- Remaining daily tokens/requests display after processing

## Project Overview
cereproc.py is a document processing tool that leverages Cerebras AI models to transform large documents through intelligent chunking and LLM processing. The tool supports:
- Multiple chunking strategies (text, semantic, markdown, code)
- Metadata extraction and validation
- Rate limiting and backoff strategies
- Atomic file writing with frontmatter preservation
- Comprehensive error handling and validation

## Architecture
- CLI framework: Fire
- Token counting: tiktoken with cl100k_base encoding
- Frontmatter handling: python-frontmatter
- Structured outputs: Cerebras JSON schema validation
- Logging: loguru for verbose mode debugging