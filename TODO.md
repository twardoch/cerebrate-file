# Cerebrate File TODO - Issues #102 Implementation

## ✅ Phase 1: Add Rich Dependency and Basic UI Components - COMPLETED ✅
- [x] Add `rich>=13.0.0` to dependencies in `pyproject.toml`
- [x] Remove `tqdm>=4.66.0` from dependencies in `pyproject.toml`
- [x] Create `src/cerebrate_file/ui.py` module for UI components
- [x] Create `FileProgressDisplay` class to manage two-row output
- [x] Create progress bar helper functions
- [x] Design minimalistic two-row display system with no borders
- [x] Create tests for UI components in `tests/test_ui.py`

## ✅ Phase 2: Replace Current Progress System with Rich UI - COMPLETED ✅
- [x] Replace `tqdm` import and usage in `cerebrate_file.py:15`
- [x] Update `process_document()` function to use rich progress callbacks
- [x] Modify `cli.py` to use new progress display
- [x] Update `make_cerebras_request()` to trigger progress callbacks
- [x] Maintain verbose/quiet mode compatibility
- [x] Test progress display with single file processing
- [x] Ensure two-row display shows: input path + progress, output path + remaining calls

## ✅ Phase 3: Extend CLI Interface for Recursive Processing - COMPLETED ✅
- [x] Add `--recurse` parameter to CLI `run()` function signature
- [x] Add `--workers` parameter to CLI `run()` function signature (default: 4)
- [x] Update `validate_inputs()` in `config.py` to handle directory inputs
- [x] Add validation for `recurse` parameter in `config.py`
- [x] Implement directory vs file detection logic
- [x] Update help text and CLI documentation
- [x] Test CLI accepts new parameters without breaking existing usage

## Phase 4: Implement Recursive File Discovery
- [ ] Create `src/cerebrate_file/recursive.py` module
- [ ] Implement `find_files_recursive()` function using `pathlib.Path.rglob(pattern)`
- [ ] Create `replicate_directory_structure()` function
- [ ] Add directory structure replication logic
- [ ] Create file list generation and validation
- [ ] Handle edge cases: no matches, permission errors, invalid patterns
- [ ] Test recursive file discovery with various glob patterns
- [ ] Test output directory structure correctly replicates input structure

## Phase 5: Implement Parallel Processing Pipeline
- [ ] Create parallel processing coordinator using `concurrent.futures.ThreadPoolExecutor`
- [ ] Implement `process_files_parallel()` function
- [ ] Integrate with existing `process_document()` function
- [ ] Implement worker pool management with configurable worker count
- [ ] Add progress aggregation across multiple files
- [ ] Handle worker exceptions and failures gracefully
- [ ] Update progress display to show multiple files
- [ ] Test parallel processing with different worker counts

## Phase 6: Integration and UI Enhancement
- [ ] Integrate recursive processing with rich UI
- [ ] Update `FileProgressDisplay` to handle multiple files
- [ ] Enhance progress display for multiple files
- [ ] Add overall progress tracking: `Processing file X of Y`
- [ ] Implement remaining API calls calculation across files
- [ ] Aggregate remaining API calls across all files
- [ ] Maintain individual file progress in two-row format
- [ ] Test rich UI works seamlessly with parallel processing

## Phase 7: Testing and Documentation
- [ ] Create `tests/test_recursive.py` for recursive processing tests
- [ ] Create comprehensive tests for new functionality
- [ ] Update existing tests to work with rich UI
- [ ] Test with various glob patterns and directory structures
- [ ] Test parallel processing with different worker counts
- [ ] Update integration tests to cover new workflows
- [ ] Test edge cases and error conditions:
  - [ ] Empty directories
  - [ ] Invalid glob patterns
  - [ ] Permission denied scenarios
  - [ ] Network failures during parallel processing
  - [ ] Very large directory structures
  - [ ] Files with special characters in names
- [ ] Update documentation and help text
- [ ] Verify all existing CLI options work unchanged

## Validation Checklist
- [ ] Rich UI displays correctly in various terminals
- [ ] Parallel processing completes successfully
- [ ] Directory structure replication is accurate
- [ ] Error handling prevents cascading failures
- [ ] Performance scales appropriately with worker count
- [ ] Existing single-file processing unchanged
- [ ] All CLI options work as documented
- [ ] Memory usage remains reasonable for large directories
- [ ] All tests pass including new functionality
- [ ] Edge cases properly handled and tested
- [ ] Documentation accurately reflects new features

## Quality Assurance
- [ ] All new modules under 200 lines
- [ ] Comprehensive type hints for all functions
- [ ] Detailed docstrings following existing patterns
- [ ] Error handling with proper logging
- [ ] Unit tests for all public functions
- [ ] No regression in existing functionality
- [ ] Code follows project style guidelines
- [ ] Dependencies justified and minimal