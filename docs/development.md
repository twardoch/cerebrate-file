---
layout: default
title: Development
nav_order: 9
---

# Development
{: .no_toc }

Contributing to Cerebrate File development
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Getting Started

### Prerequisites

- Python 3.9+ (recommended: 3.12)
- uv package manager
- Git
- GitHub account (for contributions)

### Setting Up Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/twardoch/cerebrate-file.git
   cd cerebrate-file
   ```

2. **Create virtual environment:**
   ```bash
   uv venv --python 3.12
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   uv pip install -e .
   uv add --dev pytest pytest-cov pytest-mock rich loguru
   ```

4. **Set up pre-commit hooks (optional but recommended):**
   ```bash
   uv add --dev pre-commit
   pre-commit install
   ```

## Project Structure

```
cerebrate-file/
├── src/
│   └── cerebrate_file/
│       ├── __init__.py         # Package initialization
│       ├── cli.py              # CLI interface
│       ├── api_client.py       # Cerebras API client
│       ├── cerebrate_file.py   # Core processing logic
│       ├── chunking.py         # Chunking strategies
│       ├── config.py           # Configuration management
│       ├── constants.py        # Constants and defaults
│       ├── models.py           # Data models
│       ├── recursive.py        # Recursive processing
│       ├── tokenizer.py        # Token counting
│       ├── ui.py              # UI components
│       └── utils.py           # Utility functions
├── tests/
│   ├── test_api_client.py     # API client tests
│   ├── test_chunking.py       # Chunking tests
│   ├── test_cli.py            # CLI tests
│   ├── test_config.py         # Configuration tests
│   ├── test_integration.py    # Integration tests
│   ├── test_recursive.py      # Recursive processing tests
│   └── test_ui.py             # UI component tests
├── docs/                      # Documentation (Jekyll)
├── examples/                  # Example scripts
├── pyproject.toml             # Package configuration
├── README.md                  # Project README
├── CHANGELOG.md               # Version history
├── LICENSE                    # Apache 2.0 license
└── .gitignore                 # Git ignore rules
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow the coding standards and guidelines below.

### 3. Write Tests

Every new feature must have tests:

```python
# tests/test_your_feature.py
import pytest
from cerebrate_file.your_module import your_function

def test_your_function():
    """Test basic functionality."""
    result = your_function("input")
    assert result == "expected"

def test_your_function_edge_case():
    """Test edge cases."""
    with pytest.raises(ValueError):
        your_function(None)
```

### 4. Run Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=cerebrate_file --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_your_feature.py -xvs

# Run tests in watch mode
uvx pytest-watch
```

### 5. Check Code Quality

```bash
# Format code
uvx ruff format src/ tests/

# Lint code
uvx ruff check src/ tests/ --fix

# Type checking
uvx mypy src/cerebrate_file

# Security scan
uvx bandit -r src/
```

### 6. Update Documentation

- Update relevant documentation in `docs/`
- Update README.md if needed
- Add to CHANGELOG.md

### 7. Commit Changes

```bash
git add .
git commit -m "feat: add your feature description"
```

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code restructuring
- `test:` Tests
- `chore:` Maintenance

### 8. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Coding Standards

### Python Style Guide

Follow PEP 8 with these specifics:

```python
# this_file: src/cerebrate_file/example.py
"""Module docstring describing purpose."""

from typing import Optional, List, Dict
from pathlib import Path

# Constants in UPPER_CASE
DEFAULT_CHUNK_SIZE = 32000
MAX_RETRIES = 3

class ExampleClass:
    """Class docstring with description."""

    def __init__(self, param: str) -> None:
        """Initialize with parameter."""
        self.param = param

    def process(self, data: str) -> str:
        """
        Process data with clear description.

        Args:
            data: Input data to process

        Returns:
            Processed result

        Raises:
            ValueError: If data is invalid
        """
        if not data:
            raise ValueError("Data cannot be empty")

        # Clear comment explaining logic
        result = self._transform(data)
        return result

    def _transform(self, data: str) -> str:
        """Private method with underscore prefix."""
        return data.upper()
```

### Type Hints

Always use type hints:

```python
from typing import Optional, List, Dict, Union, Tuple

def process_files(
    paths: List[Path],
    options: Optional[Dict[str, str]] = None
) -> Tuple[List[str], List[str]]:
    """Process multiple files."""
    successes: List[str] = []
    failures: List[str] = []

    for path in paths:
        try:
            result = process_single(path, options or {})
            successes.append(result)
        except Exception as e:
            failures.append(str(e))

    return successes, failures
```

### Error Handling

Use specific exceptions:

```python
class CerebrateError(Exception):
    """Base exception for cerebrate-file."""
    pass

class ConfigurationError(CerebrateError):
    """Configuration related errors."""
    pass

class APIError(CerebrateError):
    """API related errors."""
    pass

def validate_config(config: Dict) -> None:
    """Validate configuration."""
    if not config.get("api_key"):
        raise ConfigurationError("API key is required")

    if config.get("chunk_size", 0) < 1000:
        raise ConfigurationError("Chunk size must be at least 1000")
```

### Logging

Use loguru for logging:

```python
from loguru import logger

def process_document(path: str, verbose: bool = False) -> str:
    """Process document with logging."""
    if verbose:
        logger.enable("cerebrate_file")
    else:
        logger.disable("cerebrate_file")

    logger.debug(f"Processing {path}")

    try:
        result = do_processing(path)
        logger.info(f"Successfully processed {path}")
        return result
    except Exception as e:
        logger.error(f"Failed to process {path}: {e}")
        raise
```

### Documentation

Write comprehensive docstrings:

```python
def complex_function(
    input_data: str,
    chunk_size: int = 32000,
    strategy: str = "markdown"
) -> List[str]:
    """
    Split input data into processable chunks.

    This function takes large input data and splits it into smaller
    chunks suitable for processing by the AI model. It maintains
    context between chunks using overlap samples.

    Args:
        input_data: The raw input text to be chunked
        chunk_size: Maximum size of each chunk in tokens (default: 32000)
        strategy: Chunking strategy - 'text', 'semantic', 'markdown', or 'code'

    Returns:
        List of text chunks ready for processing

    Raises:
        ValueError: If input_data is empty or strategy is invalid
        TokenLimitError: If a single unit exceeds chunk_size

    Examples:
        >>> chunks = complex_function("Long text...", chunk_size=16000)
        >>> len(chunks)
        3

        >>> chunks = complex_function("# Markdown", strategy="markdown")
        >>> chunks[0].startswith("#")
        True

    Note:
        The actual chunk size may be slightly smaller than specified
        to avoid breaking in the middle of sentences or code blocks.
    """
```

## Testing Guidelines

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch
from cerebrate_file.module import function_to_test

class TestFeatureName:
    """Test suite for feature."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_data = "sample"

    def test_normal_case(self):
        """Test normal operation."""
        result = function_to_test(self.test_data)
        assert result == "expected"

    def test_edge_case(self):
        """Test edge cases."""
        assert function_to_test("") == ""
        assert function_to_test(None) is None

    @pytest.mark.parametrize("input,expected", [
        ("test1", "result1"),
        ("test2", "result2"),
        ("test3", "result3"),
    ])
    def test_multiple_cases(self, input, expected):
        """Test multiple scenarios."""
        assert function_to_test(input) == expected

    def test_error_handling(self):
        """Test error conditions."""
        with pytest.raises(ValueError, match="Invalid input"):
            function_to_test("invalid")

    @patch('cerebrate_file.module.external_function')
    def test_with_mock(self, mock_func):
        """Test with mocked dependencies."""
        mock_func.return_value = "mocked"
        result = function_to_test("input")
        mock_func.assert_called_once_with("input")
        assert result == "mocked"
```

### Integration Tests

```python
# tests/test_integration.py
import tempfile
from pathlib import Path
from cerebrate_file import process_document

def test_end_to_end_processing():
    """Test complete processing pipeline."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text("# Test\nContent")

        # Process
        output_file = Path(tmpdir) / "output.md"
        process_document(
            input_data=str(input_file),
            output_data=str(output_file),
            prompt="Add emoji"
        )

        # Verify
        assert output_file.exists()
        content = output_file.read_text()
        assert "Test" in content
```

## Performance Optimization

### Profiling

```python
import cProfile
import pstats
from io import StringIO

def profile_function():
    """Profile function performance."""
    profiler = cProfile.Profile()
    profiler.enable()

    # Code to profile
    result = expensive_function()

    profiler.disable()
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
    print(stream.getvalue())

    return result
```

### Memory Optimization

```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    """Monitor memory usage."""
    # Process in chunks to reduce memory
    for chunk in generate_chunks(large_data):
        process_chunk(chunk)
        del chunk  # Explicit cleanup

def generate_chunks(data, chunk_size=1000):
    """Generator to avoid loading all data."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]
```

## Release Process

### 1. Update Version

Edit `pyproject.toml`:
```toml
[project]
version = "1.1.0"
```

### 2. Update Changelog

Add to `CHANGELOG.md`:
```markdown
## [1.1.0] - 2024-01-15

### Added
- New feature description

### Changed
- Modified behavior

### Fixed
- Bug fixes
```

### 3. Run Tests

```bash
python -m pytest --cov=cerebrate_file
```

### 4. Build Package

```bash
uv build
```

### 5. Test Package

```bash
uv pip install dist/cerebrate_file-1.1.0-py3-none-any.whl
cerebrate-file --version
```

### 6. Tag Release

```bash
git tag -a v1.1.0 -m "Release version 1.1.0"
git push origin v1.1.0
```

### 7. Publish to PyPI

```bash
uv publish
```

## Contributing Guidelines

### Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Report inappropriate behavior

### Pull Request Process

1. **Fork** the repository
2. **Create** feature branch
3. **Write** tests for new code
4. **Ensure** all tests pass
5. **Update** documentation
6. **Submit** pull request

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Coverage maintained

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-reviewed code
- [ ] Updated documentation
- [ ] Added to CHANGELOG.md
```

## Debugging Tips

### Using pdb

```python
import pdb

def debug_function(data):
    """Debug with pdb."""
    pdb.set_trace()  # Breakpoint
    result = process(data)
    return result
```

### Verbose Logging

```python
from loguru import logger
import sys

# Configure detailed logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"
)
```

### Environment Variables

```bash
# Enable debug mode
export CEREBRATE_DEBUG=1
export LOGURU_LEVEL=DEBUG

# Run with debugging
python -m cerebrate_file.cli --verbose
```

## Resources

### Documentation
- [Python Packaging Guide](https://packaging.python.org)
- [pytest Documentation](https://docs.pytest.org)
- [Type Hints PEP 484](https://www.python.org/dev/peps/pep-0484/)

### Tools
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [ruff](https://github.com/charliermarsh/ruff) - Fast Python linter
- [mypy](http://mypy-lang.org/) - Static type checker
- [pre-commit](https://pre-commit.com/) - Git hook framework

### Community
- [GitHub Discussions](https://github.com/twardoch/cerebrate-file/discussions)
- [Issue Tracker](https://github.com/twardoch/cerebrate-file/issues)
- [Pull Requests](https://github.com/twardoch/cerebrate-file/pulls)

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0