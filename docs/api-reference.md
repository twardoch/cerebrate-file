# API Reference

Python API documentation for programmatic usage.

## Overview

Cerebrate File works as a CLI tool but can also be used programmatically. This reference covers the main modules and functions available.

## Installation for API Use

```python
# Install the package
pip install cerebrate-file

# Import in Python
from cerebrate_file import process_document, CerebrasClient
from cerebrate_file.chunking import ChunkingStrategy, create_chunks
from cerebrate_file.config import Config
```

## Core Functions

### process_document

Main function for processing documents.

```python
from cerebrate_file import process_document

def process_document(
    input_data: str,
    output_data: Optional[str] = None,
    file_prompt: Optional[str] = None,
    prompt: Optional[str] = None,
    chunk_size: int = 32000,
    max_tokens_ratio: int = 100,
    data_format: str = "markdown",
    sample_size: int = 200,
    temp: float = 0.7,
    top_p: float = 0.8,
    model: str = "zai-glm-4.6",
    verbose: bool = False,
    explain: bool = False,
    dry_run: bool = False,
    api_key: Optional[str] = None
) -> str:
    """
    Process a document using Cerebras AI.

    Args:
        input_data: Path to input file
        output_data: Path to output file (optional)
        file_prompt: Path to prompt file (optional)
        prompt: Direct prompt text (optional)
        chunk_size: Maximum tokens per chunk
        max_tokens_ratio: Output token ratio
        data_format: Chunking strategy
        sample_size: Context overlap size
        temp: Model temperature
        top_p: Nucleus sampling parameter
        model: Model name
        verbose: Enable verbose logging
        explain: Extract metadata
        dry_run: Test without API calls
        api_key: Cerebras API key (optional)

    Returns:
        Processed document text

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If configuration is invalid
        APIError: If Cerebras API fails
    """
```

**Example Usage:**

```python
from cerebrate_file import process_document

# Basic processing
result = process_document(
    input_data="document.md",
    prompt="Summarize each section",
    output_data="summary.md"
)

# Advanced processing
result = process_document(
    input_data="report.pdf.txt",
    file_prompt="instructions.md",
    chunk_size=48000,
    data_format="semantic",
    temp=0.5,
    verbose=True
)
```

## Classes

### CerebrasClient

Client for interacting with Cerebras API.

```python
from cerebrate_file.api_client import CerebrasClient

class CerebrasClient:
    """Client for Cerebras API interactions."""

    def __init__(self, api_key: str, model: str = "zai-glm-4.6"):
        """
        Initialize Cerebras client.

        Args:
            api_key: Cerebras API key
            model: Model name to use
        """

    def create_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float = 0.7,
        top_p: float = 0.8,
        stream: bool = True
    ) -> Union[str, Iterator[str]]:
        """
        Create a completion from the model.

        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            stream: Whether to stream response

        Returns:
            Completion text or stream iterator
        """
```

**Example Usage:**

```python
from cerebrate_file.api_client import CerebrasClient

# Initialize client
client = CerebrasClient(api_key="csk-...")

# Create completion
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain quantum computing."}
]

response = client.create_completion(
    messages=messages,
    max_tokens=1000,
    temperature=0.98
)

# Handle streaming response
for chunk in response:
    print(chunk, end="")
```

### ChunkingStrategy

Strategies for splitting documents into chunks.

```python
from cerebrate_file.chunking import ChunkingStrategy

class ChunkingStrategy:
    """Base class for chunking strategies."""

    @abstractmethod
    def split(self, text: str, max_tokens: int) -> List[str]:
        """Split text into chunks."""
        pass

# Available strategies
from cerebrate_file.chunking import (
    TextChunker,      # Simple text splitting
    SemanticChunker,  # Paragraph-aware
    MarkdownChunker,  # Markdown structure-aware
    CodeChunker       # Code structure-aware
)
```

**Example Usage:**

```python
from cerebrate_file.chunking import MarkdownChunker

# Create chunker
chunker = MarkdownChunker()

# Split document
text = open("document.md").read()
chunks = chunker.split(text, max_tokens=32000)

for i, chunk in enumerate(chunks, 1):
    print(f"Chunk {i}: {len(chunk)} characters")
```

### Config

Configuration management.

```python
from cerebrate_file.config import Config

class Config:
    """Configuration container."""

    def __init__(self, **kwargs):
        """Initialize configuration."""

    def validate(self) -> None:
        """Validate configuration values."""

    @classmethod
    def from_cli(cls, **kwargs) -> "Config":
        """Create config from CLI arguments."""
```

**Example Usage:**

```python
from cerebrate_file.config import Config

# Create configuration
config = Config(
    input_data="document.md",
    output_data="output.md",
    chunk_size=32000,
    temp=0.7,
    top_p=0.8
)

# Validate
config.validate()

# Access values
print(f"Chunk size: {config.chunk_size}")
print(f"Temperature: {config.temp}")
```

## Utility Functions

### Token Counting

Count tokens in text.

```python
from cerebrate_file.tokenizer import count_tokens

def count_tokens(text: str) -> int:
    """
    Count tokens in text using Qwen tokenizer.

    Args:
        text: Text to count tokens for

    Returns:
        Number of tokens
    """

# Example
text = "This is a sample text."
token_count = count_tokens(text)
print(f"Tokens: {token_count}")
```

### File I/O

Read and write files with proper encoding.

```python
from cerebrate_file.utils import read_file, write_file

def read_file(path: str) -> str:
    """Read file with UTF-8 encoding."""

def write_file(path: str, content: str) -> None:
    """Write file with UTF-8 encoding."""

# Example
content = read_file("input.txt")
processed = content.upper()
write_file("output.txt", processed)
```

### Frontmatter Handling

Parse and update frontmatter in markdown files.

```python
from cerebrate_file.frontmatter import parse_frontmatter, update_frontmatter

def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """
    Parse frontmatter from content.

    Returns:
        Tuple of (metadata dict, body text)
    """

def update_frontmatter(content: str, metadata: Dict) -> str:
    """
    Update or add frontmatter to content.

    Args:
        content: Document content
        metadata: Metadata dictionary

    Returns:
        Content with updated frontmatter
    """

# Example
metadata, body = parse_frontmatter(content)
metadata["processed_date"] = "2024-01-01"
updated = update_frontmatter(content, metadata)
```

## Advanced Usage

### Custom Processing Pipeline

Create a custom processing pipeline:

```python
from cerebrate_file import CerebrasClient
from cerebrate_file.chunking import MarkdownChunker
from cerebrate_file.tokenizer import count_tokens
import os

class CustomProcessor:
    """Custom document processor."""

    def __init__(self, api_key: str):
        self.client = CerebrasClient(api_key)
        self.chunker = MarkdownChunker()

    def process_with_validation(self, input_path: str, output_path: str):
        """Process document with validation."""

        # Read input
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Validate size
        tokens = count_tokens(content)
        if tokens > 100000:
            raise ValueError(f"Document too large: {tokens} tokens")

        # Create chunks
        chunks = self.chunker.split(content, max_tokens=32000)

        # Process each chunk
        results = []
        for chunk in chunks:
            response = self.client.create_completion(
                messages=[
                    {"role": "user", "content": chunk}
                ],
                max_tokens=32000
            )
            results.append(response)

        # Combine results
        output = "\n\n".join(results)

        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output)

        return output

# Usage
processor = CustomProcessor(api_key=os.getenv("CEREBRAS_API_KEY"))
processor.process_with_validation("input.md", "output.md")
```

### Batch Processing

Process multiple files programmatically:

```python
from cerebrate_file import process_document
from pathlib import Path
import concurrent.futures

def process_batch(file_paths: List[str], prompt: str, workers: int = 4):
    """Process multiple files in parallel."""

    def process_file(path):
        try:
            output_path = f"processed_{Path(path).name}"
            process_document(
                input_data=path,
                output_data=output_path,
                prompt=prompt
            )
            return f"✓ {path}"
        except Exception as e:
            return f"✗ {path}: {e}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        results = executor.map(process_file, file_paths)

    for result in results:
        print(result)

# Usage
files = Path(".").glob("*.md")
process_batch(list(files), "Improve clarity", workers=4)
```

### Error Handling

Implement robust error handling:

```python
from cerebrate_file import process_document
from cerebrate_file.exceptions import (
    APIError,
    RateLimitError,
    TokenLimitError,
    NetworkError
)
import time

def process_with_retry(input_path: str, max_retries: int = 3):
    """Process with automatic retry on failure."""

    for attempt in range(max_retries):
        try:
            return process_document(
                input_data=input_path,
                prompt="Process this document"
            )

        except RateLimitError as e:
            wait_time = 2 ** attempt * 60  # Exponential backoff
            print(f"Rate limited. Waiting {wait_time} seconds...")
            time.sleep(wait_time)

        except TokenLimitError as e:
            print(f"Token limit exceeded: {e}")
            # Try with smaller chunks
            return process_document(
                input_data=input_path,
                prompt="Process this document",
                chunk_size=16000  # Smaller chunks
            )

        except NetworkError as e:
            print(f"Network error: {e}")
            time.sleep(10)  # Brief wait

        except APIError as e:
            print(f"API error: {e}")
            raise  # Don't retry API errors

    raise Exception(f"Failed after {max_retries} attempts")

# Usage
try:
    result = process_with_retry("document.md")
    print("Success!")
except Exception as e:
    print(f"Failed: {e}")
```

### Custom Chunking

Implement custom chunking logic:

```python
from cerebrate_file.chunking import ChunkingStrategy
from typing import List

class CustomChunker(ChunkingStrategy):
    """Custom chunking implementation."""

    def split(self, text: str, max_tokens: int) -> List[str]:
        """Split by custom logic."""
        chunks = []

        # Split by double newlines (paragraphs)
        paragraphs = text.split("\n\n")

        current_chunk = ""
        for para in paragraphs:
            # Check if adding paragraph exceeds limit
            if len(current_chunk) + len(para) > max_tokens * 4:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

# Usage
chunker = CustomChunker()
chunks = chunker.split(document_text, max_tokens=8000)
```

## Integration Examples

### Flask Web App

Integrate with a Flask web application:

```python
from flask import Flask, request, jsonify
from cerebrate_file import process_document
import tempfile
import os

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process_endpoint():
    """Process document via API."""
    try:
        # Get file and prompt
        file = request.files['document']
        prompt = request.form.get('prompt', '')

        # Save temporarily
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file.save(tmp.name)
            temp_path = tmp.name

        # Process
        result = process_document(
            input_data=temp_path,
            prompt=prompt
        )

        # Clean up
        os.unlink(temp_path)

        return jsonify({
            'success': True,
            'result': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
```

### Jupyter Notebook

Use in Jupyter notebooks:

```python
# Cell 1: Setup
from cerebrate_file import process_document
import os

# Set API key
os.environ['CEREBRAS_API_KEY'] = 'csk-...'

# Cell 2: Process document
result = process_document(
    input_data='notebook_content.md',
    prompt='Summarize key points',
    verbose=True
)

# Cell 3: Display result
from IPython.display import Markdown
display(Markdown(result))
```

## Best Practices

1. **Error Handling**: Always wrap API calls in try-except blocks
2. **Rate Limiting**: Implement backoff and retry logic
3. **Token Management**: Check token counts before processing
4. **Memory Usage**: Process large batches in chunks
5. **API Key Security**: Never hardcode API keys
6. **Logging**: Use verbose mode for debugging
7. **Testing**: Test with small files first
8. **Validation**: Validate inputs before processing

## Next Steps

- Review [Examples](examples/) for practical usage
- Check [Troubleshooting](troubleshooting/) for common issues
- See [CLI Reference](cli-reference/) for command-line usage
- Explore [Configuration](configuration/) for optimization