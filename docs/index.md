---
layout: home
title: Home
nav_order: 1
description: "Process large documents with Cerebras AI using intelligent chunking and context preservation"
permalink: /
---

# Cerebrate File Documentation
{: .fs-9 }

Break large files into manageable pieces, preserve context, and process them with Cerebras AI.
{: .fs-6 .fw-300 }

[Get started](#getting-started){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 } [View on GitHub](https://github.com/twardoch/cerebrate-file){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## Overview

**Cerebrate File** is a command-line tool for processing large documents through the Cerebras AI API. It splits files intelligently to fit within the model’s context window while keeping track of what came before.

### Key Features

- **Smart chunking**: Automatically break large documents into smaller parts
- **Context overlap**: Keep snippets from previous chunks to maintain continuity
- **Directory support**: Recursively process folders using glob patterns
- **Parallel execution**: Handle multiple files at once with threading
- **Terminal UI**: Clean progress output that updates in real time
- **Retry logic**: Handle rate limits and temporary errors without manual intervention
- **Format flexibility**: Works with text, markdown, code, and semantic content
- **Configurable behavior**: Plenty of CLI options for tuning how things work

## Getting Started

### Installation

Install with pip or uv:

```bash
# Using pip
pip install cerebrate-file

# Using uv (faster)
uv pip install cerebrate-file
```

### Quick Start

1. Set your Cerebras API key:
   ```bash
   export CEREBRAS_API_KEY="csk-..."
   ```

2. Process a single file:
   ```bash
   cerebrate-file document.md --output processed.md
   ```

3. Process all markdown files in a directory tree:
   ```bash
   cerebrate-file . --output ./output --recurse "**/*.md"
   ```

## Use Cases

Use Cerebrate File when you need to:

- Rewrite, summarize, or translate large documents
- Refactor code across an entire project
- Generate new versions or expansions of existing content
- Apply consistent transformations to many files at once
- Clean, format, or analyze large text datasets

## Model Details

The tool uses the **Qwen-3 Coder 480B** model from Cerebras:

- **Context window**: 131,072 tokens
- **Speed**: ~570 tokens/second
- **Specialty**: Good at both code and natural language
- **Rate limits**:
  - 30 requests per minute
  - 1,000 requests per day
  - 10 million tokens per minute

## Documentation Sections

- **[Installation](installation/)** – Setup instructions
- **[Usage Guide](usage/)** – Practical examples
- **[CLI Reference](cli-reference/)** – All command-line flags and options
- **[Configuration](configuration/)** – Settings and tuning tips
- **[Examples](examples/)** – Real-world workflows
- **[API Reference](api-reference/)** – For Python integration
- **[Troubleshooting](troubleshooting/)** – Fixes for common issues
- **[Development](development/)** – How to contribute

## System Requirements

- Python 3.9+
- Minimum 4GB RAM (8GB recommended for large files)
- Internet connection
- Valid Cerebras API key

## License

Licensed under Apache 2.0. See [LICENSE](https://github.com/twardoch/cerebrate-file/blob/main/LICENSE) for details.

## Support

- Report bugs or request features: [GitHub Issues](https://github.com/twardoch/cerebrate-file/issues)
- Ask questions or share ideas: [GitHub Discussions](https://github.com/twardoch/cerebrate-file/discussions)
- Maintainer: Adam Twardoch ([@twardoch](https://github.com/twardoch))