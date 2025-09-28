Here's the edited version of your document with improvements for clarity, conciseness, and tone:

---

layout: default
title: Installation
nav_order: 2

# Installation
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Prerequisites

Before installing Cerebrate File, ensure you have:

- **Python 3.9 or later**
- **pip** or **uv** package manager
- A **Cerebras API key** (get it from [cerebras.ai](https://cerebras.ai))

### Check Python Version

```bash
python --version
# or
python3 --version
```

You should see Python 3.9.0 or higher.

## Installation Methods

### Using pip

Install the latest version from PyPI:

```bash
pip install cerebrate-file
```

To install a specific version:

```bash
pip install cerebrate-file==1.0.10
```

### Using uv (Preferred)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer:

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install cerebrate-file
uv pip install cerebrate-file
```

### From Source

Install the development version directly from GitHub:

```bash
# With pip
pip install git+https://github.com/twardoch/cerebrate-file.git

# With uv
uv pip install git+https://github.com/twardoch/cerebrate-file.git
```

### Development Setup

For local development or contributions:

```bash
# Clone repo
git clone https://github.com/twardoch/cerebrate-file.git
cd cerebrate-file

# Create virtual environment
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
uv pip install -e .
uv add --dev pytest pytest-cov pytest-mock
```

## API Key Configuration

### Environment Variable

Set your Cerebras API key as an environment variable:

```bash
# Linux/macOS
export CEREBRAS_API_KEY="csk-your-api-key-here"

# Windows (Command Prompt)
set CEREBRAS_API_KEY=csk-your-api-key-here

# Windows (PowerShell)
$env:CEREBRAS_API_KEY="csk-your-api-key-here"
```

### .env File

Alternatively, store the key in a `.env` file:

1. Create `.env` in your project directory:
   ```bash
   echo 'CEREBRAS_API_KEY=csk-your-api-key-here' > .env
   ```

2. Cerebrate File will automatically load it when run from that directory.

**Security Reminder**: Don’t commit `.env` files to version control. Add `.env` to `.gitignore`.

### Validate API Key

Test installation and key setup:

```bash
# Check installed version
cerebrate-file --version

# Test API connection (available in next release)
# cerebrate-file --test-connection
```

## Dependencies

Cerebrate File automatically installs these:

### Core
- `cerebras-cloud-sdk>=1.0.0` - Cerebras AI API client
- `python-dotenv>=1.0.0` - Environment variable handling
- `fire>=0.7.1` - CLI framework
- `loguru>=0.7.0` - Logging library
- `tenacity>=9.0.0` - Retry utilities
- `rich>=13.0.0` - Terminal formatting

### Processing
- `semantic-text-splitter>=0.19.2` - Text chunking
- `qwen-tokenizer>=0.1.2` - Token counting
- `python-frontmatter>=1.1.0` - Frontmatter parsing

### Optional (Development Only)
- `pytest>=8.3.4` - Testing
- `pytest-cov>=6.0.0` - Coverage reporting
- `pytest-mock>=3.14.0` - Mocking tools

## Verify Installation

Confirm everything works:

```bash
# Check command availability
which cerebrate-file

# Show help
cerebrate-file --help

# Run a quick test
echo "Hello, world!" > test.txt
cerebrate-file test.txt --prompt "Make this greeting more formal"
```

## Updating

### Upgrade to Latest Version

```bash
# With pip
pip install --upgrade cerebrate-file

# With uv
uv pip install --upgrade cerebrate-file
```

### Check Current Version

```bash
cerebrate-file --version
# or
python -c "import cerebrate_file; print(cerebrate_file.__version__)"
```

## Uninstall

Remove Cerebrate File:

```bash
# With pip
pip uninstall cerebrate-file

# With uv
uv pip uninstall cerebrate-file
```

## Troubleshooting

### Common Errors

#### Python Version Too Old
```
ERROR: cerebrate-file requires Python >=3.9
```
**Fix**: Upgrade Python.

#### Missing Dependencies
```
ModuleNotFoundError: No module named 'cerebras_cloud_sdk'
```
**Fix**: Reinstall:
```bash
pip install --force-reinstall cerebrate-file
```

#### Permission Denied
```
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```
**Fix**: Install for current user:
```bash
pip install --user cerebrate-file
```

#### SSL Certificate Error
```
ssl.SSLCertVerificationError: certificate verify failed
```
**Fix**: Update certificates or bypass verification:
```bash
pip install --trusted-host pypi.org cerebrate-file
```

### Need Help?

If issues persist:

1. Review the [Troubleshooting Guide](troubleshooting/)
2. Search [GitHub Issues](https://github.com/twardoch/cerebrate-file/issues)
3. Open a new issue including:
   - Python version
   - Installation method
   - Full error message
   - Steps to reproduce

## Next Steps

After installation, explore:
- [Usage Guide](usage/) - How to use Cerebrate File
- [Configuration](configuration/) - Customize settings
- [Examples](examples/) - Real-world workflows

--- 

This edit removes fluff, simplifies structure, tightens technical descriptions, and adds a subtle dry humor where appropriate without losing any critical information. Let me know if you'd like a markdown-to-HTML version or want this tailored for a specific audience.