
# Changelog

## [Unreleased] - 2025-09-20



### Changed

- Migrated `tool.uv.dev-dependencies` to `[dependency-groups].dev` to fix uv deprecation warning

- Relaxed `max_tokens_ratio` upper bound; effective cap still enforced by `MAX_OUTPUT_TOKENS` at runtime



### Added

- STDIN/STDOUT streaming support with `--input_data -` and `--output_data -` options

  - Incompatible with `--recurse` flag

  - Added test coverage and documentation examples

- Built-in prompt library in `prompts/` folder

  - Includes `fix-pdf-extracted-text.xml` for cleaning PDF text

  - Smart resolution: checks direct paths first, then library

  - Supports any file extension

  - Lists available prompts on error

  - Full test coverage

- Pre-screening for recursive processing

  - Shows accurate file counts and filters existing outputs when `--force=False`

  - Clear messaging and accurate progress bars

  - Minimal performance overhead

  - Full test coverage

- `--force` flag to prevent accidental overwriting

  - Checks before API calls to save quota

  - Works in both single-file and recursive modes

  - Clear messaging for skipped files

  - Doesn't affect in-place editing

  - Full test coverage

- Comprehensive GitHub Pages documentation

  - Jekyll-based site with Just-the-Docs theme

  - Includes installation, usage, API reference, examples, and development guides

- `testapi.py` script for API key and quota verification

### Fixed

- **Pydantic Plugin ImportError**: Resolved by ensuring execution in an isolated environment to prevent loading incompatible external plugins.

- **Rate Limit Display**: Fixed incorrect token calculation; now shows only actual remaining daily requests from API headers.

- **Zero-Output Safeguards**: Added chunk-level diagnostics and aborts processing if total output tokens are zero to prevent overwriting files with empty content.



## [1.0.10] - 2025-09-20



### Added

- **Rich UI Support**: Replaced tqdm with rich for enhanced terminal UI

  - Two-row progress display

  - `FileProgressDisplay` for single files and `MultiFileProgressDisplay` for parallel processing

  - Progress callback architecture

  - 98% test coverage (18 tests)

- **Recursive Processing Infrastructure**: Added `--recurse` for glob patterns and `--workers` for parallel processing

  - Comprehensive validation for inputs

  - Directory structure replication for outputs



### Changed

- **Dependencies**: Added `rich>=13.0.0`, removed `tqdm`.

- **CLI Interface**: Extended `run()` with `--recurse` and `--workers`. Input/output paths now support directories.

- **Processing Pipeline**: Modified `process_document()` to use progress callbacks.



### Technical Improvements

- Added comprehensive test suite for UI components (18 tests, 98% coverage).

- Full type hints for new functions and classes.

- Clean separation of UI and logic via callbacks.

- Maintained 100% backward compatibility.

- Enhanced error messages.



### Test Results

- 33 core tests passing.

- 18% overall test coverage (focused on new features).

## [2.0.0] - 2025-09-19



### Changed

- **Complete Package Restructure**: Refactored monolithic `cereproc.py` (1788 lines) into a modular package.

- **Module Architecture**: Created 10+ focused modules.



### Added

- **Test Coverage**: 29% overall coverage with 45 passing tests.

- **Test Framework**: Robust testing infrastructure for unit tests, edge cases, and error handling.



### Technical Improvements

- **Better Error Handling**: Comprehensive exception hierarchy.

- **Dependency Injection**: TokenizerManager for better testability.

- **Strategy Pattern**: Clean chunking strategy implementation.

- **Type Safety**: Full type hints throughout codebase.

- **Validation**: Enhanced input validation.

- **Backup Support**: File operations support automatic backups.

- **Code Structure**: Single responsibility, minimal dependencies, and improved testability.

- **Graceful Degradation**: Better handling of optional dependencies.

- **Atomic Operations**: Enhanced file safety with proper cleanup.



## [1.2.2] - 2025-09-19



### Clarified

- Refined focus on the essential workflow: parsing, chunking, metadata explanation, LLM processing, and saving.



### Removed

- Removed unnecessary complexity and features not aligned with the core purpose.



## [1.2.1] - 2025-09-19



### Added

- **Remaining Tokens Display**: Shows estimated remaining daily tokens and requests after processing, including rate limit info, token capacity estimates, and an 80% quota warning.

## [1.2.0] - 2025-09-19



### Added

- **Code-Aware Chunking**: Intelligent code splitting that respects function, class, and structural boundaries, tracking brace/parenthesis depth.

- **Dry-Run Mode**: `--dry-run` flag for testing chunking strategies, displaying analysis, token counts, and API request previews without making calls.

- **Input Validation**: Comprehensive validation for files, chunk size, token ratio, API keys, and data format with clear error messages.



## [1.1.1] - 2025-09-19



### Fixed

- Preserved frontmatter in output when using `--explain` mode.

- Ensured metadata information only prints in verbose mode for cleaner output.

- Displayed the input file path at the start of processing.



## [1.1.0] - 2025-09-19



### Added

- **--explain Mode**: New functionality for document metadata processing, including Jekyll-style frontmatter parsing, validation, structured JSON output, and metadata context inclusion in prompts.



### Dependencies

- Added python-frontmatter for Jekyll-style frontmatter parsing.

## [1.0.0] - 2025-09-19



### Added

- Initial release of `cereproc.py` CLI tool for processing large documents with Cerebras.

- Implemented four chunking strategies: text, semantic, markdown, and code.

- Added intelligent continuity system to maintain context across chunks.

- Integrated token-accurate accounting, rate limiting, and streaming API with retry logic.

- Included comprehensive logging, environment variable management, and robust error handling.



### Technical Architecture

- Single-file design with a functional programming approach.

- Integrated semantic-text-splitter for intelligent boundary detection.

- Enforced token budget limits (32K input / 40K completion) and extracted continuity examples.



### Testing & Documentation

- Comprehensive test suite and documentation (SPEC.md, README.md).



### Dependencies

- fire, loguru, python-dotenv, tenacity, cerebras-cloud-sdk, semantic-text-splitter, qwen-tokenizer.



### Performance

- Processes 1000-3000 tokens/second with 95%+ token accuracy and coherent chunk transitions.
