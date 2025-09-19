---
this_file: PLAN.md
---

# Plan: Fix Critical Issues in cerebrate-file (Issue #104)

## Problem Analysis

Three critical bugs identified in cerebrate-file processing:

1. **Call Counting Bug**: API response shows "172,799 calls remaining" after each call - indicates broken call counting logic
2. **Missing YAML Frontmatter**: Despite `--explain` flag, output files sometimes lack frontmatter metadata
3. **Explain Mode Chunk Processing**: First chunk not processed with real prompt in explain mode - metadata processing interferes with content processing

## Technical Root Causes

### Call Counting Issue
- Likely in API response parsing logic in src/cerebrate_file/cli.py
- Response header parsing or usage tracking may be incorrect
- Could be caching stale values or parsing wrong field

### Frontmatter Issue
- Explain mode metadata processing may be overwriting or skipping frontmatter generation
- Race condition between metadata extraction and content processing
- Frontmatter construction logic may have conditional bugs

### Chunk Processing Issue
- First chunk gets processed for metadata extraction but then skipped for content processing
- Need to ensure first chunk gets processed with both metadata prompt AND real prompt
- Current flow: metadata processing ’ content processing, but first chunk missing from content

## Implementation Plan

### Phase 1: Investigate Current Code
- Read src/cerebrate_file/cli.py to understand current processing flow
- Identify API response parsing logic for call counting
- Map explain mode processing workflow
- Understand how chunks are processed in explain vs normal mode

### Phase 2: Fix Call Counting Bug
- Locate API response parsing code
- Fix usage/call count extraction from Cerebras API response
- Ensure proper header parsing or JSON field extraction
- Test with dry run to verify counting logic

### Phase 3: Fix Frontmatter Issue
- Ensure explain mode always generates frontmatter
- Fix conditional logic that may skip frontmatter creation
- Verify frontmatter preservation/generation in all code paths

### Phase 4: Fix Chunk Processing
- Modify explain mode to process first chunk with real prompt after metadata extraction
- Ensure all chunks get processed with actual user prompt
- Maintain metadata processing while adding content processing for first chunk

### Phase 5: Testing & Validation
- Create test with explain mode on sample files
- Verify call counting shows correct values
- Confirm frontmatter appears in all explain mode outputs
- Ensure all chunks processed correctly

## Success Criteria

- Call counting shows accurate, decreasing values per API call
- All explain mode outputs contain proper YAML frontmatter
- First chunk processed with real prompt in explain mode
- No regressions in normal processing mode
- Test script runs successfully with expected outputs

## Dependencies

- cerebras-cloud-sdk (for API response structure)
- python-frontmatter (for frontmatter handling)
- Existing test data in testdata/ directory

## Testing Strategy

- Use existing test2.sh script to reproduce issues
- Add verbose logging to trace processing flow
- Create minimal test case for each bug
- Verify fix with original failing command