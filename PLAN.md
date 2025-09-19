# Issues #102 Implementation Plan

## Project Overview and Objectives

**Project Scope**: Implement minimal `rich` UI support and recursive file processing for cerebrate-file package based on issues/102.txt requirements.

**Core Objectives**:
- **Task A**: Replace current progress output with minimal rich two-row microtable
- **Task B**: Add recursive directory processing with glob patterns and parallel workers
- Maintain existing CLI interface compatibility
- Keep UI extremely minimalistic with no borders, but allow color
- Preserve all existing functionality while adding new features

## Technical Architecture Decisions

### Task A: Rich UI Implementation

**Current State Analysis**:
- Package uses `tqdm` for progress bars in `cerebrate_file.py:15`
- Simple print statements for status updates in `cli.py`
- No rich dependency currently exists

**Target Design**:
- Two-row microtable for each file being processed:
  - Row 1: `[input_path] [progress_bar]`
  - Row 2: `[output_path] [remaining_api_calls]`
- Minimal styling, no borders, colors allowed
- Replace existing tqdm usage

### Task B: Recursive Processing Implementation

**Current State Analysis**:
- CLI only accepts single file input (`input_data: str`)
- Single-threaded processing in `process_document()`
- No directory structure replication support

**Target Design**:
- New `--recurse=GLOB_PATTERN` option
- Input becomes folder path when `--recurse` is specified
- Optional `--workers` parameter (default: 4)
- Output folder replicates input directory structure
- Parallel processing using `concurrent.futures`

## Implementation Phases

### Phase 1: Add Rich Dependency and Basic UI Components
**Priority**: High | **Dependencies**: None

**Tasks**:
- Add `rich>=13.0.0` to dependencies in `pyproject.toml`
- Create `src/cerebrate_file/ui.py` module for UI components
- Create progress bar helper functions
- Design minimalistic two-row display system

**Implementation Details**:
- Use `rich.progress.Progress` with custom columns
- Create `FileProgressDisplay` class to manage two-row output
- Integrate with existing processing pipeline
- Remove `tqdm` dependency and usage

**Package Selection Rationale**:
- **rich**: Chosen for flexible progress bars, minimal overhead, excellent terminal output
- **concurrent.futures**: Standard library for parallel processing
- **pathlib**: Modern path handling for directory operations

**Success Criteria**:
- Rich dependency installed and working
- Basic two-row progress display functional
- No regression in existing functionality

### Phase 2: Replace Current Progress System with Rich UI
**Priority**: High | **Dependencies**: Phase 1

**Tasks**:
- Update `cerebrate_file.py` to use rich instead of tqdm
- Modify `cli.py` to use new progress display
- Create progress update callbacks for API calls
- Test progress display with single file processing

**Implementation Details**:
- Replace `tqdm` import and usage in `cerebrate_file.py:15`
- Integrate progress updates in `process_document()` function
- Update `make_cerebras_request()` to trigger progress callbacks
- Maintain verbose/quiet mode compatibility

**Success Criteria**:
- Rich progress bars work for single file processing
- Two-row display shows: input path + progress, output path + remaining calls
- All existing CLI options work unchanged

### Phase 3: Extend CLI Interface for Recursive Processing
**Priority**: Medium | **Dependencies**: Phase 2

**Tasks**:
- Add `--recurse` and `--workers` parameters to CLI
- Modify input validation to handle directories
- Update help text and documentation
- Implement directory vs file detection logic

**Implementation Details**:
- Update `cli.py:run()` function signature:
  ```python
  def run(
      input_data: str,
      # ... existing params ...
      recurse: Optional[str] = None,  # glob pattern
      workers: int = 4,  # parallel workers
  ):
  ```
- Add validation for `recurse` parameter in `config.py`
- Update `validate_inputs()` to handle directory inputs

**Success Criteria**:
- CLI accepts new parameters without breaking existing usage
- Input validation works for both files and directories
- Help text accurately describes new options

### Phase 4: Implement Recursive File Discovery
**Priority**: Medium | **Dependencies**: Phase 3

**Tasks**:
- Create `src/cerebrate_file/recursive.py` module
- Implement glob pattern matching using `pathlib`
- Add directory structure replication logic
- Create file list generation and validation

**Implementation Details**:
- Use `pathlib.Path.rglob(pattern)` for recursive file matching
- Implement `find_files_recursive()` function:
  ```python
  def find_files_recursive(
      input_dir: Path,
      pattern: str
  ) -> List[Tuple[Path, Path]]:
      """Find files matching pattern and compute output paths."""
  ```
- Create `replicate_directory_structure()` function
- Handle edge cases: no matches, permission errors, invalid patterns

**Success Criteria**:
- Recursive file discovery works with various glob patterns
- Output directory structure correctly replicates input structure
- Proper error handling for invalid patterns and permissions

### Phase 5: Implement Parallel Processing Pipeline
**Priority**: Medium | **Dependencies**: Phase 4

**Tasks**:
- Create parallel processing coordinator
- Integrate with existing `process_document()` function
- Implement worker pool management
- Add progress aggregation across multiple files

**Implementation Details**:
- Use `concurrent.futures.ThreadPoolExecutor` for I/O-bound operations
- Create `process_files_parallel()` function:
  ```python
  def process_files_parallel(
      file_pairs: List[Tuple[Path, Path]],
      workers: int,
      progress_callback: Callable
  ) -> ProcessingResults:
  ```
- Update progress display to show multiple files
- Handle worker exceptions and failures gracefully

**Success Criteria**:
- Parallel processing works with configurable worker count
- Progress display updates correctly for multiple files
- Error handling prevents single file failures from stopping entire process

### Phase 6: Integration and UI Enhancement
**Priority**: Medium | **Dependencies**: Phase 5

**Tasks**:
- Integrate recursive processing with rich UI
- Enhance progress display for multiple files
- Add overall progress tracking
- Implement remaining API calls calculation across files

**Implementation Details**:
- Update `FileProgressDisplay` to handle multiple files
- Show overall progress: `Processing file X of Y`
- Aggregate remaining API calls across all files
- Maintain individual file progress in two-row format

**Success Criteria**:
- Rich UI works seamlessly with parallel processing
- Overall and per-file progress clearly displayed
- Remaining API calls accurately calculated and displayed

### Phase 7: Testing and Documentation
**Priority**: High | **Dependencies**: Phase 6

**Tasks**:
- Create comprehensive tests for new functionality
- Update existing tests to work with rich UI
- Test edge cases and error conditions
- Update documentation and help text

**Implementation Details**:
- Create `tests/test_recursive.py` for recursive processing
- Create `tests/test_ui.py` for rich UI components
- Test with various glob patterns and directory structures
- Test parallel processing with different worker counts
- Update integration tests to cover new workflows

**Success Criteria**:
- All tests pass including new functionality
- Edge cases properly handled and tested
- Documentation accurately reflects new features

## Technical Specifications

### Rich UI Component Design

```python
# src/cerebrate_file/ui.py
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
from rich.console import Console

class FileProgressDisplay:
    def __init__(self):
        self.console = Console()
        self.progress = Progress(
            TextColumn("{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            console=self.console
        )

    def update_file_progress(self, input_path: str, output_path: str,
                           progress: float, remaining_calls: int):
        """Update two-row progress display."""
        # Row 1: input path + progress bar
        # Row 2: output path + remaining calls
```

### Recursive Processing Interface

```python
# src/cerebrate_file/recursive.py
from pathlib import Path
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

def find_files_recursive(input_dir: Path, pattern: str) -> List[Tuple[Path, Path]]:
    """Find files matching glob pattern and generate output paths."""

def process_files_parallel(
    file_pairs: List[Tuple[Path, Path]],
    workers: int,
    processing_params: dict,
    progress_callback: callable
) -> dict:
    """Process multiple files in parallel with progress tracking."""
```

### CLI Interface Extension

```python
# Updated cli.py:run() signature
def run(
    input_data: str,
    output_data: Optional[str] = None,
    # ... existing parameters ...
    recurse: Optional[str] = None,  # NEW: glob pattern for recursive processing
    workers: int = 4,               # NEW: number of parallel workers
) -> None:
    """Enhanced to support recursive directory processing."""
```

## Dependencies and Package Justification

### New Dependencies

1. **rich>=13.0.0**
   - **Why**: Modern, flexible terminal UI with excellent progress bars
   - **Alternatives considered**: tqdm (current), alive-progress, enlighten
   - **Selection rationale**: Rich provides the most flexible two-row display system with minimal overhead

### Updated Dependencies

1. **Remove or keep tqdm>=4.66.0**
   - **Decision**: Remove tqdm, fully replace with rich
   - **Reason**: Avoid dependency bloat, rich provides superior functionality

### Standard Library Usage

1. **concurrent.futures.ThreadPoolExecutor**
   - **Why**: I/O-bound operations benefit from threading
   - **Alternative**: ProcessPoolExecutor (for CPU-bound, but file processing is I/O-bound)

2. **pathlib.Path.rglob()**
   - **Why**: Modern, robust recursive file pattern matching
   - **Alternative**: glob.glob() with recursive=True

## Testing and Validation Criteria

### Unit Testing Strategy
- Test recursive file discovery with various glob patterns
- Test rich UI components in isolation
- Test parallel processing coordination
- Mock API calls to test progress tracking

### Integration Testing Strategy
- Test full recursive processing pipeline
- Test CLI compatibility with existing and new options
- Test error handling across parallel workers
- Performance testing with large directory structures

### Edge Cases to Test
- Empty directories
- Invalid glob patterns
- Permission denied scenarios
- Network failures during parallel processing
- Very large directory structures
- Files with special characters in names

### Validation Checklist
- [ ] Rich UI displays correctly in various terminals
- [ ] Parallel processing completes successfully
- [ ] Directory structure replication is accurate
- [ ] Error handling prevents cascading failures
- [ ] Performance scales appropriately with worker count
- [ ] Existing single-file processing unchanged
- [ ] All CLI options work as documented
- [ ] Memory usage remains reasonable for large directories

## Risk Assessment and Mitigation

### High Risk Areas
1. **Rich UI compatibility across terminals**
   - Mitigation: Test on various terminal types, provide fallback
   - Test matrix: Terminal.app, iTerm2, Windows Terminal, Linux terminals

2. **Parallel processing resource management**
   - Mitigation: Proper worker pool cleanup, resource monitoring
   - Add configurable limits and timeouts

3. **Directory structure replication accuracy**
   - Mitigation: Extensive testing with complex directory hierarchies
   - Handle edge cases: symlinks, permissions, special characters

### Medium Risk Areas
1. **Performance with large directory structures**
   - Mitigation: Implement streaming discovery, memory-efficient processing
2. **API rate limiting with parallel requests**
   - Mitigation: Coordinate rate limiting across workers

### Mitigation Strategies
- Comprehensive error handling at each level
- Graceful degradation for UI components
- Resource cleanup in all exit paths
- Extensive logging for debugging issues
- Progress persistence for long-running operations

## Implementation Guidelines

### Code Quality Standards
- All new modules under 200 lines
- Comprehensive type hints for all functions
- Detailed docstrings following existing patterns
- Error handling with proper logging
- Unit tests for all public functions

### Dependency Management
- Minimal new dependencies (only rich)
- Graceful handling of missing optional features
- Clear separation between UI and core logic
- Backward compatibility for existing CLI usage

### Performance Considerations
- Efficient file discovery using pathlib
- Appropriate worker pool sizing
- Memory-efficient progress tracking
- Minimal UI update frequency to reduce overhead

## Future Considerations

### Extensibility Points
- Pluggable progress display implementations
- Configurable worker pool types (thread vs process)
- Custom glob pattern engines
- Progress persistence for resume capability

### Performance Optimizations
- Async/await for truly concurrent I/O
- Memory-mapped file processing for large files
- Intelligent worker pool auto-sizing
- Progress batching for reduced UI overhead

### Maintenance Improvements
- Configuration file support for default options
- Advanced logging with structured output
- Metrics collection for performance analysis
- Better error reporting with suggested fixes