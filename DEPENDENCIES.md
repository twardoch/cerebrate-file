# Dependencies

## Core Dependencies

### fire (>=0.5.0)
- **Purpose**: CLI framework for creating command-line interfaces
- **Why chosen**: Simple, pythonic, generates help automatically from function signatures
- **Usage**: Main CLI interface in `cli.py`

### loguru (>=0.7.0)
- **Purpose**: Structured logging with minimal configuration
- **Why chosen**: Superior to standard logging with better formatting and simpler API
- **Usage**: Throughout the codebase for debug/info/warning/error logging

### python-dotenv (>=1.0.0)
- **Purpose**: Load environment variables from .env file
- **Why chosen**: Standard solution for environment management
- **Usage**: Loading CEREBRAS_API_KEY and other configuration

### tenacity (>=8.2.0)
- **Purpose**: Retry logic with exponential backoff
- **Why chosen**: Robust, configurable retry mechanisms for API calls
- **Usage**: API client retry logic in `api_client.py`

### cerebras-cloud-sdk (>=1.0.0)
- **Purpose**: Official Cerebras API client
- **Why chosen**: Required for Cerebras API integration
- **Usage**: Core API communication in `api_client.py`

### semantic-text-splitter (>=0.15.0)
- **Purpose**: Intelligent text chunking at semantic boundaries
- **Why chosen**: Better chunking quality than simple character splits
- **Usage**: Semantic chunking strategy in `chunking.py`

### qwen-tokenizer (>=0.8.0)
- **Purpose**: Accurate token counting for Qwen models
- **Why chosen**: Official tokenizer for accurate token budget management
- **Usage**: Token counting throughout processing pipeline
- **Note**: Graceful fallback to estimation if unavailable

### python-frontmatter (>=1.0.0)
- **Purpose**: Parse Jekyll-style YAML frontmatter
- **Why chosen**: Standard library for frontmatter parsing
- **Usage**: Metadata extraction in explain mode

### rich (>=13.0.0)
- **Purpose**: Enhanced terminal UI with progress bars and formatting
- **Why chosen**: Superior to tqdm with flexible multi-line progress displays
- **Usage**: Progress display in `ui.py` for file processing visualization
- **Replaces**: tqdm (removed)

## Development Dependencies

### pytest (>=7.0.0)
- **Purpose**: Testing framework
- **Why chosen**: Industry standard Python testing
- **Usage**: All test files in `tests/` directory

### pytest-cov (>=4.0.0)
- **Purpose**: Code coverage measurement
- **Why chosen**: Integration with pytest for coverage reports
- **Usage**: Measuring test coverage

### pytest-mock (>=3.0.0)
- **Purpose**: Mocking utilities for tests
- **Why chosen**: Simplifies mocking in pytest tests
- **Usage**: Mocking API calls and file operations in tests

## Removed Dependencies

### tqdm
- **Removed in**: v2.1.0
- **Reason**: Replaced by rich for more flexible progress displays
- **Replacement**: rich.progress module

## Dependency Justification

### Why These Specific Dependencies?

1. **Minimal Dependencies**: Only 9 runtime dependencies, each serving a specific purpose
2. **Well-Maintained**: All packages have active maintenance and strong community support
3. **Single Responsibility**: Each dependency handles one specific aspect
4. **No Redundancy**: No overlapping functionality between packages
5. **Graceful Degradation**: Optional dependencies (qwen-tokenizer) have fallbacks

### Build vs Buy Decisions

- **Rich vs Custom Progress**: Rich provides battle-tested terminal UI components
- **Tenacity vs Custom Retry**: Tenacity handles complex retry scenarios professionally
- **Fire vs Argparse**: Fire reduces boilerplate and maintains cleaner code
- **Semantic-text-splitter vs Custom**: Specialized library with better algorithms

### Security Considerations

- All dependencies from PyPI official repository
- Regular updates for security patches
- No dependencies with known vulnerabilities
- Minimal transitive dependencies

## Installation

```bash
# Install all dependencies
uv sync

# Or install manually
uv add fire loguru python-dotenv tenacity cerebras-cloud-sdk semantic-text-splitter qwen-tokenizer python-frontmatter rich

# Development dependencies
uv add --dev pytest pytest-cov pytest-mock
```