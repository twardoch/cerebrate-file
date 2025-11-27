
# Changelog

## [Unreleased] - 2025-09-20

### Changed
- Migrated `tool.uv.dev-dependencies` to `[dependency-groups].dev`.
- Relaxed `max_tokens_ratio` validation; runtime cap remains unchanged.

### Added
- STDIN/STDOUT streaming support with `--input_data -` and `--output_data -` (incompatible with `--recurse`).
- Built-in prompt library in `prompts/` folder, which is checked after direct paths. Includes `fix-pdf-extracted-text.xml`.
- Pre-screening for recursive processing to show accurate file counts and filter existing outputs.
- `--force` flag to prevent accidental overwriting by checking before API calls (does not affect in-place editing).
- Comprehensive documentation.
- `testapi.py` script for API key and quota verification.

### Fixed
- **Pydantic Plugin ImportError**: Resolved by ensuring an isolated execution environment.
- **Rate Limit Display**: Fixed incorrect token calculation to show actual remaining daily requests.
- **Zero-Output Safeguards**: Added processing abort if total output is zero to prevent overwriting files with empty content.

## [1.0.10] - 2025-09-20

### Added
- **Rich UI Support**: Replaced `tqdm` with `rich` for an enhanced terminal UI, including `FileProgressDisplay` and `MultiFileProgressDisplay` with a progress callback architecture.
- **Recursive Processing**: Added `--recurse` for glob patterns and `--workers` for parallel processing with directory structure replication for outputs.

### Changed
- **Dependencies**: Added `rich>=13.0.0`, removed `tqdm`.
- **CLI Interface**: Extended `run()` with `--recurse` and `--workers`. Input/output paths now support directories.
- **Processing Pipeline**: Modified `process_document()` to use progress callbacks and enhanced error messages.

## [2.0.0] - 2025-09-19

### Changed
- **Complete Package Restructure**: Refactored monolithic `cereproc.py` (1788 lines) into a modular package with 10+ focused modules.

### Added
- A robust test framework with 45 passing tests.
- A comprehensive exception hierarchy.
- A `TokenizerManager` for dependency injection.
- A clean chunking strategy pattern.
- Full type hints throughout the codebase.
- Enhanced input validation.
- Automatic backup support for file operations.
- Improved file safety with atomic operations and better handling of optional dependencies.
## [1.2.1] - 2025-09-19

### Added
- **Remaining Tokens Display**: Shows estimated remaining daily tokens, requests, and quota status after processing.

## [1.2.0] - 2025-09-19

### Added
- **Code-Aware Chunking**: Splits code respecting function, class, and structural boundaries.
- **Dry-Run Mode**: `--dry-run` flag to preview chunking analysis and API requests without making calls.
- **Input Validation**: Comprehensive validation for files, chunk sizes, API keys, and data formats.

## [1.1.1] - 2025-09-19

### Fixed
- Preserved frontmatter in output when using `--explain` mode.
- Metadata information now only prints in verbose mode.
- Displayed the input file path at the start of processing.

## [1.1.0] - 2025-09-19

### Added
- **--explain Mode**: Processes document metadata, including Jekyll-style frontmatter parsing and structured JSON output.

### Dependencies
- Added `python-frontmatter`.

## [1.0.0] - 2025-09-19

### Added
- Initial release of `cereproc.py` CLI tool for processing large documents with Cerebras.
- Implemented four chunking strategies: text, semantic, markdown, and code.
- Added an intelligent continuity system to maintain context across chunks.
- Integrated token-accurate accounting, rate limiting, and a streaming API with retry logic.
- Included comprehensive logging, environment variable management, and error handling.

### Dependencies
- fire, loguru, python-dotenv, tenacity, cerebras-cloud-sdk, semantic-text-splitter, qwen-tokenizer.