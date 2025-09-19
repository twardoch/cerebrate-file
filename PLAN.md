# Cerebrate File Refactoring Plan

## Project Overview and Objectives

**Project Scope**: Refactor the monolithic `old/cereproc.py` (1788 lines) into a well-structured Python package with ~10 modules of ~200 lines each, while preserving all functionality and improving maintainability.

**Core Objectives**:
- Break down large monolithic file into logical, focused modules
- Maintain exact same CLI interface and functionality
- Improve code organization and maintainability
- Enable easier testing and future enhancements
- Follow Python packaging best practices

## Technical Architecture Decisions

### Module Structure Analysis

Based on analysis of `old/cereproc.py`, the code can be logically grouped into these functional areas:

1. **Data Models** (3 classes, ~50 lines)
2. **Text Processing & Tokenization** (~200 lines)
3. **Chunking Strategies** (4 functions, ~300 lines)
4. **Continuity Management** (~100 lines)
5. **API Communication** (~200 lines)
6. **Configuration & Validation** (~250 lines)
7. **File I/O & Metadata** (~150 lines)
8. **CLI Interface** (~100 lines)
9. **Main Processing Logic** (~300 lines)
10. **Constants & Utilities** (~100 lines)



## Phase-by-Phase Breakdown

### Phase 1: Setup and Constants Module
**Priority**: High | **Dependencies**: None

**Tasks**:
- Create `constants.py` with model limits, schemas, patterns
- Extract all constants from cereproc.py
- Define shared error classes
- Setup proper logging configuration

**Implementation Details**:
- `MAX_CONTEXT_TOKENS = 131000`
- `MAX_OUTPUT_TOKENS = 40000`
- `DEFAULT_CHUNK_SIZE = 32000`
- `REQUIRED_METADATA_FIELDS`
- `METADATA_SCHEMA`
- Boundary patterns for code chunking

**Success Criteria**:
- All constants centralized
- No magic numbers in other modules
- Consistent logging setup

### Phase 2: Data Models Module
**Priority**: High | **Dependencies**: constants.py

**Tasks**:
- Create `models.py` with dataclasses
- Extract `Chunk`, `RateLimitStatus`, `ProcessingState`
- Add proper type hints and documentation
- Ensure immutability where appropriate

**Implementation Details**:
- `@dataclass` classes with proper defaults
- Type hints for all fields
- Validation methods where needed
- JSON serialization support

**Success Criteria**:
- All data models in one place
- Proper typing throughout
- Clear documentation

### Phase 3: Tokenizer Module
**Priority**: High | **Dependencies**: models.py, constants.py

**Tasks**:
- Create `tokenizer.py` for text processing
- Extract `encode_text()`, `decode_tokens_safely()`
- Handle qwen-tokenizer dependency gracefully
- Add fallback mechanisms

**Implementation Details**:
- Graceful handling of missing qwen-tokenizer
- Character-based fallback implementation
- Error handling and logging
- Performance optimizations

**Success Criteria**:
- Tokenization works with and without qwen-tokenizer
- Proper error handling
- Performance maintained

### Phase 4: File Utilities Module
**Priority**: High | **Dependencies**: models.py, constants.py

**Tasks**:
- Create `file_utils.py` for I/O operations
- Extract file reading, writing, frontmatter parsing
- Include `read_file_safely()`, `write_output_atomically()`
- Handle `parse_frontmatter_content()`, `check_metadata_completeness()`

**Implementation Details**:
- Atomic file operations
- Frontmatter parsing with python-frontmatter
- Metadata validation
- Path handling with pathlib

**Success Criteria**:
- Safe file operations
- Metadata handling works correctly
- Error recovery mechanisms

### Phase 5: Configuration Module
**Priority**: High | **Dependencies**: constants.py, file_utils.py

**Tasks**:
- Create `config.py` for validation and setup
- Extract `validate_environment()`, `validate_inputs()`
- Include `setup_logging()`
- Environment variable handling

**Implementation Details**:
- Comprehensive input validation
- Environment setup and checking
- Logging configuration
- User-friendly error messages

**Success Criteria**:
- Robust input validation
- Clear error messages
- Proper environment setup

### Phase 6: Chunking Module
**Priority**: Medium | **Dependencies**: models.py, tokenizer.py, constants.py

**Tasks**:
- Create `chunking.py` with all strategies
- Extract `chunk_text_mode()`, `chunk_semantic_mode()`, etc.
- Include `create_chunks()` dispatcher
- Maintain strategy pattern

**Implementation Details**:
- Four chunking strategies: text, semantic, markdown, code
- Strategy pattern for extensibility
- Token-aware chunking
- Boundary detection for code

**Success Criteria**:
- All chunking strategies work
- Easy to add new strategies
- Proper token counting

### Phase 7: Continuity Module
**Priority**: Medium | **Dependencies**: models.py, tokenizer.py, constants.py

**Tasks**:
- Create `continuity.py` for context management
- Extract `extract_continuity_examples()`, `build_continuity_block()`
- Include `fit_continuity_to_budget()`
- Manage token budgets

**Implementation Details**:
- Context preservation between chunks
- Token budget management
- Template-based continuity blocks
- Fallback when budget exceeded

**Success Criteria**:
- Continuity works across chunks
- Respects token limits
- Graceful degradation

### Phase 8: API Client Module
**Priority**: Medium | **Dependencies**: models.py, constants.py

**Tasks**:
- Create `api_client.py` for Cerebras communication
- Extract `make_cerebras_request()`, `parse_rate_limit_headers()`
- Include `calculate_backoff_delay()`, `explain_metadata_with_llm()`
- Handle rate limiting and retries

**Implementation Details**:
- Cerebras SDK integration
- Rate limit parsing and handling
- Retry logic with tenacity
- Streaming support

**Success Criteria**:
- API communication works reliably
- Rate limiting respected
- Proper error handling

### Phase 9: Main Processing Logic
**Priority**: Medium | **Dependencies**: All above modules

**Tasks**:
- Create new `cerebrate_file.py` with core logic
- Extract main processing pipeline from `run()`
- Include `prepare_chunk_messages()`, `calculate_completion_budget()`
- Orchestrate all components

**Implementation Details**:
- Main processing pipeline
- Message preparation
- Progress tracking
- Result aggregation

**Success Criteria**:
- Core functionality preserved
- Clean separation of concerns
- Easy to test and modify

### Phase 10: CLI Interface
**Priority**: Low | **Dependencies**: cerebrate_file.py, config.py

**Tasks**:
- Create `cli.py` with Fire-based interface
- Extract CLI argument handling
- Create `__main__.py` entry point
- Preserve exact same CLI API

**Implementation Details**:
- Fire-based CLI (preserve existing interface)
- Argument validation and parsing
- Help text and usage examples
- Entry point configuration

**Success Criteria**:
- Identical CLI behavior
- Good help documentation
- Proper entry points

### Phase 11: Package Integration
**Priority**: Low | **Dependencies**: All modules

**Tasks**:
- Update `__init__.py` with proper exports
- Add dependencies to pyproject.toml
- Create proper entry points
- Integration testing

**Implementation Details**:
- Clean package interface
- Dependency management
- Entry point configuration
- Version handling

**Success Criteria**:
- Package installs correctly
- All functionality accessible
- Dependencies resolved

## Testing and Validation Criteria

### Unit Testing Strategy
- Test each module independently
- Mock external dependencies (Cerebras API, file system)
- Validate all chunking strategies
- Test error handling paths

### Integration Testing Strategy
- Test full pipeline with sample files
- Verify CLI compatibility
- Test with and without optional dependencies
- Performance regression testing

### Validation Checklist
- [ ] All original functionality preserved
- [ ] CLI interface identical
- [ ] Dependencies properly managed
- [ ] Error handling maintained
- [ ] Performance not degraded
- [ ] Code coverage maintained
- [ ] Documentation updated

## Risk Assessment and Mitigation

### High Risk Areas
1. **Token counting accuracy** - Critical for chunking
   - Mitigation: Extensive testing with various inputs
   - Fallback mechanisms for missing tokenizer

2. **API rate limiting** - Complex logic
   - Mitigation: Careful extraction and testing
   - Preserve exact timing behavior

3. **File I/O atomicity** - Data safety
   - Mitigation: Maintain atomic operations
   - Test failure scenarios

### Medium Risk Areas
1. **Continuity context** - Complex state management
2. **Frontmatter parsing** - Metadata handling
3. **Chunking strategy selection** - Strategy pattern complexity

### Mitigation Strategies
- Incremental refactoring with tests at each step
- Preserve original file as reference
- Comprehensive integration testing
- Performance benchmarking

## Implementation Guidelines

### Code Quality Standards
- Maximum 200 lines per file (except main processing)
- Comprehensive type hints
- Detailed docstrings for all public functions
- Error handling with proper logging
- No circular dependencies

### Dependency Management
- Minimize inter-module dependencies
- Use dependency injection where needed
- Clear separation of concerns
- Graceful handling of optional dependencies

### Testing Requirements
- Unit tests for each module
- Integration tests for full pipeline
- Mock external services
- Test error conditions
- Performance benchmarks

## Phase 12: Documentation and Website
**Priority**: Medium | **Dependencies**: Phase 11

**Tasks**:
- Create @docs folder with Github Pages Jekyll documentation
- Write comprehensive documentation for the project
- Update README.md with new documentation structure
- Include usage examples and API documentation

**Implementation Details**:
- Jekyll-based documentation site
- Clear navigation and structure
- Examples and tutorials
- API reference documentation

**Success Criteria**:
- Complete documentation website
- Updated README.md
- Clear usage examples

## Phase 13: Testing and Validation
**Priority**: High | **Dependencies**: All previous phases

**Tasks**:
- Create unit tests for each module
- Create integration tests for full pipeline
- Test CLI compatibility with original
- Test with and without optional dependencies
- Run performance regression testing
- Verify all original functionality preserved
- Test error handling paths
- Validate code coverage maintained

**Implementation Details**:
- Comprehensive test suite
- Mock external dependencies
- Performance benchmarking
- Error condition testing
- CI/CD integration

**Success Criteria**:
- All tests passing
- Code coverage > 80%
- Performance maintained
- Error handling verified

## Phase 14: Final Cleanup and Documentation
**Priority**: Medium | **Dependencies**: Phase 13

**Tasks**:
- Update documentation for new structure
- Clean up old cereproc.py references
- Update README.md with new usage
- Update CHANGELOG.md with refactoring notes
- Verify all imports work correctly
- Run final integration tests
- Clean up any temporary files

**Implementation Details**:
- Final documentation pass
- Code cleanup
- Integration verification
- Release preparation

**Success Criteria**:
- Clean, documented codebase
- All references updated
- Ready for release

## Future Considerations

### Extensibility Points
- Plugin system for chunking strategies
- Configurable API backends
- Custom tokenizer support
- Additional metadata formats

### Performance Optimizations
- Async API calls for parallel processing
- Streaming file processing for large documents
- Caching for repeated operations
- Memory optimization for large chunks

### Maintenance Improvements
- Better error messages and diagnostics
- Configuration file support
- Logging improvements
- Metrics collection (optional)