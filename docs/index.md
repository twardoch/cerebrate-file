---
layout: home
title: Home
nav_order: 1
description: "Cerebrate File is a powerful CLI tool for processing large documents with Cerebras AI"
permalink: /
---

# Cerebrate File Documentation
{: .fs-9 }

Process large documents with Cerebras AI through intelligent chunking and context preservation.
{: .fs-6 .fw-300 }

[Get started now](#getting-started){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 } [View on GitHub](https://github.com/twardoch/cerebrate-file){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## Overview

**Cerebrate File** is a command-line utility that enables you to process large documents through the Cerebras AI API by intelligently splitting them into manageable chunks while maintaining context continuity. It's designed to handle documents that exceed the model's context window limitations seamlessly.

### Key Features

- 🧩 **Intelligent Chunking**: Automatically splits large documents into processable chunks
- 🔗 **Context Preservation**: Maintains continuity between chunks with overlap samples
- 📁 **Recursive Processing**: Process entire directory trees with glob patterns
- ⚡ **Parallel Execution**: Multi-threaded processing for multiple files
- 🎨 **Rich Terminal UI**: Beautiful progress display with real-time updates
- 🔄 **Automatic Retry**: Smart handling of rate limits and transient failures
- 📊 **Multiple Formats**: Supports text, markdown, code, and semantic chunking
- 🎯 **Flexible Configuration**: Extensive CLI options for fine-tuning behavior

## Getting Started

### Installation

Install Cerebrate File using pip or uv:

```bash
# Using pip
pip install cerebrate-file

# Using uv (recommended)
uv pip install cerebrate-file
```

### Quick Start

1. **Set your Cerebras API key:**
   ```bash
   export CEREBRAS_API_KEY="csk-..."
   ```

2. **Process a single file:**
   ```bash
   cerebrate-file document.md --output processed.md
   ```

3. **Process multiple files recursively:**
   ```bash
   cerebrate-file . --output ./output --recurse "**/*.md"
   ```

## Use Cases

Cerebrate File is perfect for:

- **Document Transformation**: Rewrite, summarize, or translate large documents
- **Code Refactoring**: Process entire codebases with AI-powered transformations
- **Content Generation**: Generate variations or expansions of existing content
- **Batch Processing**: Apply consistent AI transformations across multiple files
- **Data Processing**: Clean, format, or analyze large text datasets

## Model Information

Cerebrate File uses the **Qwen-3 Coder 480B** model from Cerebras:

- **Context Window**: 131,072 tokens
- **Speed**: ~570 tokens/second
- **Specialization**: Optimized for both code and natural language
- **Rate Limits**:
  - 30 requests per minute
  - 1000 requests per day
  - 10M tokens per minute

## Documentation Structure

This documentation is organized into the following sections:

- **[Installation](installation/)** - Detailed setup instructions
- **[Usage Guide](usage/)** - Comprehensive usage examples
- **[CLI Reference](cli-reference/)** - Complete command-line options
- **[Configuration](configuration/)** - Configuration options and best practices
- **[Examples](examples/)** - Real-world usage examples
- **[API Reference](api-reference/)** - Python API documentation
- **[Troubleshooting](troubleshooting/)** - Common issues and solutions
- **[Development](development/)** - Contributing and development guide

## System Requirements

- Python 3.9 or later
- 4GB RAM minimum (8GB recommended for large files)
- Active internet connection
- Valid Cerebras API key

## License

Cerebrate File is distributed under the Apache 2.0 License. See the [LICENSE](https://github.com/twardoch/cerebrate-file/blob/main/LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/twardoch/cerebrate-file/issues)
- **Discussions**: [GitHub Discussions](https://github.com/twardoch/cerebrate-file/discussions)
- **Author**: Adam Twardoch ([@twardoch](https://github.com/twardoch))

---

<div class="text-delta">
  Last updated: {% last_modified_at %}
</div>