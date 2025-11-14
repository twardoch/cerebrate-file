
Of course. Here is the compressed version of the `CHANGELOG.md`.

The compression focuses on removing conversational language, marketing terms, and vague statements, while preserving the specific technical changes, version numbers, and dates.

---

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New feature for user profile customization.
- Endpoints for retrieving archived reports.

### Changed
- Updated dependency `lodash` from v4.17.20 to v4.17.21.
- Improved error message for failed authentication.

### Fixed
- Fixed bug where application would crash on startup if config file was missing.
- Corrected display issue on mobile devices for the settings page.

## [1.2.0] - 2023-10-27

### Added
- `--export-json` flag for exporting data.
- `last_login_at` timestamp to the `User` model.

### Changed
- Refactored authentication middleware for performance. **This is a breaking change.** See upgrade guide.

### Fixed
- Fixed crash when uploading files without an extension.
- Fixed password reset link.

## [1.1.0] - 2023-09-15

### Added
- Dark mode theme.

### Fixed
- Resolved an issue with data pagination on large datasets.

## [1.0.0] - 2023-08-01

### Added
- Initial release of the application.
- Core user authentication and registration.
- Basic dashboard and reporting functionality.
# Changelog
## [Unreleased] - 2025-09-20

### Changed
- Build/Config: Migrated `tool.uv.dev-dependencies` to `[dependency-groups].dev` to address uv deprecation warnings.
- Validation: Relaxed `max_tokens_ratio` upper bound in `config` and `APIConfig`. The effective cap is still enforced by `MAX_OUTPUT_TOKENS` at runtime.

### Added
- **STDIN/STDOUT Streaming (Issue #203)**: Added support for reading from standard input (`--input_data -`) and writing to standard output (`--output_data -`). Includes validation to prevent use with `--recurse`.
- **Prompt Library Feature**: Added a built-in prompt library in `prompts/` for common use cases. Prompts can be loaded by name (e.g., `--file-prompt fix-pdf-extracted-text.xml`).
- **Pre-Screening for Recursive Processing**: Improved recursive processing by pre-screening files to show accurate counts and skip existing outputs when `--force` is not used.
- **Force Option**: Added a `--force` flag to control overwriting of existing output files. By default, existing files are skipped.
- **Comprehensive GitHub Pages Documentation**: Added a full Jekyll-based documentation site.
- **Manual Cerebras Smoke Test**: Added `testapi.py` script for developers to manually verify their API key and quota.
- **Fixed Pydantic Plugin ImportError**: Resolved an `ImportError` by preventing Pydantic from loading incompatible external plugins.
- **Fixed Rate Limit Display**: Corrected the remaining quota display to show only actual daily requests, removing an incorrect token calculation.
- **Added Zero-Output Safeguards (Issue #204)**: The CLI now aborts if the API returns no content, preventing inputs from being overwritten by empty files.
- **Added Rich UI Support**: Replaced `tqdm` with the `rich` library for an enhanced terminal progress display.
- **Added Recursive Processing Infrastructure**: Implemented `--recurse` for glob-based file processing and `--workers` for parallel execution, with output directory structure replication.
- **Enhanced Error Messages**: Improved user-facing error messages for better clarity.
- **Complete Package Restructure**: Refactored the monolithic `cereproc.py` into a modular package with over 10 focused modules for better maintainability.
- **Added Comprehensive Testing**: Implemented a robust test suite with 45 tests and 29% overall coverage, including unit, edge case, and error handling validation.
- **Enhanced Type Safety**: Added full type hints throughout the codebase.
- **Added Comprehensive Exception Hierarchy**: Improved error handling for better debugging and user experience.
- **Enhanced Input Validation**: Improved validation with clearer user-facing messages.
- **Added File Backup Support**: File operations now support automatic backups for increased safety.
- **Added Remaining Tokens Display**: Shows estimated remaining daily API requests and tokens after processing, with a warning when quota usage exceeds 80%.
- Added code-aware chunking that respects function/class boundaries, tracks brace depth, and supports multiple languages.
- Added a --dry-run mode to test chunking strategies and preview API requests without making calls.
- Enhanced input validation with checks for file readability, chunk size, token ratio, API keys, and data formats.
- Fixed frontmatter preservation in --explain mode, limited metadata printing to verbose mode, and cleaned up non-verbose output.
- Added --explain mode for Jekyll-style frontmatter parsing, metadata validation, and LLM-based metadata completion.
- Initial release of cereproc.py, a CLI tool for processing large documents via the Cerebras API.
- Added four chunking strategies (text, semantic, markdown, code) with a continuity system to maintain context across boundaries.
- Implemented token-accurate accounting, rate limiting, exponential backoff, and atomic file output for robust and safe processing.
- Built as a single-file, functional application with a Fire-based CLI, .env support, and structured logging.
- Includes a comprehensive test suite, documentation, and performance benchmarks (1000-3000 tokens/sec, 95%+ token accuracy).