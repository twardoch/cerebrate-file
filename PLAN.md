---
this_file: PLAN.md
---

# Cerebrate-File Pre-Screening Implementation Plan

## Problem Analysis

The current implementation performs file existence checking during processing, which causes inefficient progress reporting. When `--recurse` is used, the tool shows total candidates but only checks for existing output files during progress, causing confusion and inconsistent behavior.

**Current flow:**
1. Find candidate input files (total shown)
2. Start progress
3. During processing: check if output exists + skip if `--force` not given

**Required flow:**
1. Find candidate input files
2. Pre-screening: if `--force` not given, remove files where output exists
3. Report final batch total
4. Progress through actual processing

## Technical Architecture

### Core Components

The implementation requires modifications to:

1. **CLI Layer** (`src/cerebrate_file/cli.py`): Add pre-screening stage to recursive processing
2. **Recursive Module** (`src/cerebrate_file/recursive.py`): Add pre-screening function
3. **File Utils** (`src/cerebrate_file/file_utils.py`): Utility for checking output file existence

### Implementation Strategy

**Package Dependencies:**
- No new packages required - using existing `pathlib`, `loguru`
- Leverage existing `find_files_recursive` function
- Extend current `--force` logic

## Phase-by-Phase Implementation

### Phase 1: Core Pre-Screening Function

**Task 1.1: Create pre_screen_files function**
- Location: `src/cerebrate_file/recursive.py`
- Function signature: `pre_screen_files(file_pairs: List[Tuple[Path, Path]], force: bool) -> List[Tuple[Path, Path]]`
- Logic:
  - If `force=True`, return all file_pairs unchanged
  - If `force=False`, filter out pairs where output file exists
  - Log skipped files with reason
  - Return filtered list

**Task 1.2: Add output file existence check utility**
- Location: `src/cerebrate_file/file_utils.py`
- Function: `output_file_exists(input_path: Path, output_path: Path) -> bool`
- Logic:
  - Return `False` if input_path == output_path (in-place processing)
  - Return `output_path.exists()` otherwise
  - Handle edge cases (permissions, broken symlinks)

### Phase 2: CLI Integration

**Task 2.1: Modify recursive processing in cli.py**
- Location: `src/cerebrate_file/cli.py` lines 133-139
- Changes:
  1. After `find_files_recursive()` call
  2. Add pre-screening stage if `force=False`
  3. Update progress reporting with final count
  4. Remove existing duplicate check in `process_file_wrapper`

**Task 2.2: Update progress reporting**
- Show both initial candidates and final count after pre-screening
- Format: "Found X candidates, Y will be processed (Z skipped - use --force to include)"

### Phase 3: Single File Mode Consistency

**Task 3.1: Align single file mode**
- Move single file existence check earlier in pipeline (before chunking)
- Location: `src/cerebrate_file/cli.py` lines 343-347
- Ensure consistent behavior between single and recursive modes

### Phase 4: Testing and Validation

**Task 4.1: Unit Tests**
- Test `pre_screen_files()` with various scenarios:
  - `force=True` (all files returned)
  - `force=False` + no existing outputs (all files returned)
  - `force=False` + some existing outputs (filtered list)
  - `force=False` + all existing outputs (empty list)
- Test edge cases: permission denied, broken symlinks

**Task 4.2: Integration Tests**
- Test recursive mode with pre-screening
- Test progress reporting accuracy
- Test that skipped files don't appear in progress
- Verify `--force` overrides pre-screening

**Task 4.3: Regression Tests**
- Ensure single file mode still works
- Verify dry-run mode compatibility
- Check verbose/non-verbose output consistency

## Specific Implementation Details

### Modified Functions

**1. `cli.py` run() function recursive section:**
```python
# After line 133: file_pairs = find_files_recursive(input_path, recurse, output_path)
if not force:
    original_count = len(file_pairs)
    file_pairs = pre_screen_files(file_pairs, force)
    skipped_count = original_count - len(file_pairs)

    if skipped_count > 0:
        print(f"=Ê Found {original_count} candidates, {len(file_pairs)} will be processed ({skipped_count} skipped - use --force to include)")
    else:
        print(f"=Ê Found {len(file_pairs)} files to process")
else:
    print(f"=Ê Found {len(file_pairs)} files to process")

# Remove the duplicate check in process_file_wrapper (lines 169-174)
```

**2. New function in `recursive.py`:**
```python
def pre_screen_files(
    file_pairs: List[Tuple[Path, Path]],
    force: bool
) -> List[Tuple[Path, Path]]:
    """Pre-screen file pairs, removing those with existing outputs if force=False.

    Args:
        file_pairs: List of (input_path, output_path) tuples
        force: If True, return all pairs; if False, filter existing outputs

    Returns:
        Filtered list of file pairs
    """
```

### Error Handling

- **Permission Errors**: Log warning, include file in processing (let later stage handle)
- **Broken Symlinks**: Log warning, exclude from processing
- **Missing Directories**: Include in processing (output dirs created later)

### Logging Strategy

- **INFO**: Summary of pre-screening results
- **DEBUG**: Individual file decisions during pre-screening
- **WARNING**: Permission or access issues during pre-screening

## Success Criteria

1. **Functional Requirements:**
   - Pre-screening happens before progress starts
   - Progress shows accurate total (post-screening count)
   - `--force` bypasses pre-screening
   - Single file mode behavior unchanged

2. **Performance Requirements:**
   - Pre-screening adds minimal overhead (< 100ms for 1000 files)
   - No duplicate file system calls
   - Memory usage remains constant (no additional storage of file data)

3. **User Experience:**
   - Clear indication of screening results
   - Consistent behavior between single/recursive modes
   - Informative messages about skipped files

## Risk Assessment

**Low Risk:**
- Minimal code changes required
- Leverages existing `--force` logic
- No new dependencies

**Potential Issues:**
- Race conditions if files are created/deleted during pre-screening
- Performance impact on very large file sets
- Edge cases with special file types or permissions

**Mitigation:**
- Keep pre-screening fast and simple
- Add comprehensive logging for debugging
- Extensive testing with edge cases

## Future Considerations

- **Caching**: Could cache file existence checks for repeated runs
- **Parallel Screening**: For very large file sets, could parallelize pre-screening
- **Advanced Filtering**: Could extend to other file attributes (size, age, etc.)

## Testing Strategy

1. **Write failing tests first** for new `pre_screen_files` function
2. **Implement minimal code** to pass tests
3. **Integration tests** for CLI changes
4. **Regression tests** to ensure no breakage
5. **Performance benchmarks** for large file sets

## Package Dependencies

No additional packages required. Implementation uses:
- `pathlib` for file operations
- `loguru` for logging
- `typing` for type hints
- Existing project modules

This plan implements the exact requirements from issue 201 while maintaining simplicity and ensuring robust testing.