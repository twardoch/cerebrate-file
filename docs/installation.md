---
layout: default
title: Installation
nav_order: 2
---

# Installation
{: .no_toc }

Complete guide to installing and setting up Cerebrate File
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Prerequisites

Before installing Cerebrate File, ensure you have:

- **Python 3.9 or later** installed on your system
- **pip** or **uv** package manager
- A **Cerebras API key** (obtain from [cerebras.ai](https://cerebras.ai))

### Checking Python Version

```bash
python --version
# or
python3 --version
```

You should see Python 3.9.0 or higher.

## Installation Methods

### Using pip (Traditional)

Install the latest stable version from PyPI:

```bash
pip install cerebrate-file
```

To install a specific version:

```bash
pip install cerebrate-file==1.0.10
```

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install cerebrate-file
uv pip install cerebrate-file
```

### From Source

Install the development version directly from GitHub:

```bash
# Using pip
pip install git+https://github.com/twardoch/cerebrate-file.git

# Using uv
uv pip install git+https://github.com/twardoch/cerebrate-file.git
```

### Development Installation

For contributing or local development:

```bash
# Clone the repository
git clone https://github.com/twardoch/cerebrate-file.git
cd cerebrate-file

# Create a virtual environment
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with development dependencies
uv pip install -e .
uv add --dev pytest pytest-cov pytest-mock
```

## API Key Configuration

### Setting the API Key

Cerebrate File requires a Cerebras API key. Set it as an environment variable:

```bash
# Linux/macOS
export CEREBRAS_API_KEY="csk-your-api-key-here"

# Windows (Command Prompt)
set CEREBRAS_API_KEY=csk-your-api-key-here

# Windows (PowerShell)
$env:CEREBRAS_API_KEY="csk-your-api-key-here"
```

### Using a .env File

For convenience, you can store your API key in a `.env` file:

1. Create a `.env` file in your project directory:
   ```bash
   echo 'CEREBRAS_API_KEY=csk-your-api-key-here' > .env
   ```

2. Cerebrate File will automatically load it when run from that directory.

**Security Note**: Never commit `.env` files to version control. Add `.env` to your `.gitignore` file.

### Validating Your API Key

Test your installation and API key:

```bash
# Check installation
cerebrate-file --version

# Test API connection (coming in next version)
# cerebrate-file --test-connection
```

## Dependencies

Cerebrate File automatically installs these dependencies:

### Core Dependencies
- `cerebras-cloud-sdk>=1.0.0` - Cerebras AI API client
- `python-dotenv>=1.0.0` - Environment variable management
- `fire>=0.7.1` - CLI interface
- `loguru>=0.7.0` - Logging
- `tenacity>=9.0.0` - Retry logic
- `rich>=13.0.0` - Terminal UI

### Processing Dependencies
- `semantic-text-splitter>=0.19.2` - Semantic text chunking
- `qwen-tokenizer>=0.1.2` - Token counting
- `python-frontmatter>=1.1.0` - Frontmatter parsing

### Optional Dependencies
- `pytest>=8.3.4` - Testing (development only)
- `pytest-cov>=6.0.0` - Coverage reporting (development only)
- `pytest-mock>=3.14.0` - Mocking utilities (development only)

## Verifying Installation

After installation, verify everything works:

```bash
# Check the command is available
which cerebrate-file

# Show help
cerebrate-file --help

# Process a small test file
echo "Hello, world!" > test.txt
cerebrate-file test.txt --prompt "Make this greeting more formal"
```

## Updating

### Update to Latest Version

```bash
# Using pip
pip install --upgrade cerebrate-file

# Using uv
uv pip install --upgrade cerebrate-file
```

### Check Current Version

```bash
cerebrate-file --version
# or
python -c "import cerebrate_file; print(cerebrate_file.__version__)"
```

## Uninstallation

To remove Cerebrate File:

```bash
# Using pip
pip uninstall cerebrate-file

# Using uv
uv pip uninstall cerebrate-file
```

## Troubleshooting Installation

### Common Issues

#### Python Version Error
```
ERROR: cerebrate-file requires Python >=3.9
```
**Solution**: Upgrade Python to 3.9 or later.

#### Missing Dependencies
```
ModuleNotFoundError: No module named 'cerebras_cloud_sdk'
```
**Solution**: Reinstall with dependencies:
```bash
pip install --force-reinstall cerebrate-file
```

#### Permission Denied
```
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```
**Solution**: Use user installation:
```bash
pip install --user cerebrate-file
```

#### SSL Certificate Error
```
ssl.SSLCertVerificationError: certificate verify failed
```
**Solution**: Update certificates or use trusted host:
```bash
pip install --trusted-host pypi.org cerebrate-file
```

### Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](troubleshooting/)
2. Search [GitHub Issues](https://github.com/twardoch/cerebrate-file/issues)
3. Open a new issue with:
   - Python version
   - Installation method
   - Complete error message
   - Steps to reproduce

## Next Steps

Once installed, proceed to:
- [Usage Guide](usage/) - Learn how to use Cerebrate File
- [Configuration](configuration/) - Set up your preferences
- [Examples](examples/) - See real-world examples