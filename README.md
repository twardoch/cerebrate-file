<p align="center"><img src="icon.png" alt="cerebrate-file" width="160"></p>

# cerebrate-file

Feed large documents to the Cerebras AI cloud — chunk by chunk, at inference speeds that make OpenAI look sluggish.

## The problem it solves

Cerebras runs inference on dedicated wafer-scale hardware. It is genuinely fast — thousands of tokens per second. But like every language model, it has a context window. A 100-page document does not fit in one API call.

`cerebrate-file` solves this by splitting your document into overlapping chunks, processing each one in sequence, and stitching the outputs back together. A "continuity block" carries a sample of the previous chunk's input and output into the next request, so the model knows it is in the middle of something.

## What you can use it for

Any task where you want an LLM to transform a document chunk by chunk:

- Rewrite or summarise long reports
- Apply a style guide to a manuscript
- Extract structured data from multi-page documents
- Edit Markdown files with a consistent voice
- Run any freeform instruction over content too large for one prompt

## Install

```bash
pip install cerebrate-file
# or
uv pip install cerebrate-file
```

Set your API key:

```bash
export CEREBRAS_API_KEY="csk-..."
```

## Quick start

```bash
# Process a single file (overwrites in place)
cerebrate-file document.md --prompt "Fix grammar and improve clarity"

# Write to a separate output file
cerebrate-file input.md output.md --prompt "Translate to formal English"

# Use a prompt file instead of inline text
cerebrate-file report.md --file-prompt prompts/summarize.md

# Dry run — shows chunking plan without calling the API
cerebrate-file large.md --dry-run --verbose

# Process a directory recursively
cerebrate-file ./docs --recurse "**/*.md" --prompt "Fix typos" --workers 4
```

## How chunking works

The document is split into chunks using one of five strategies selected by `--data-format`:

| Mode | Best for |
|---|---|
| `markdown` (default) | Markdown files — splits at headings and paragraphs |
| `text` | Plain prose — splits at sentence boundaries |
| `semantic` | Mixed content — semantic similarity grouping |
| `code` | Source code — splits at function/class boundaries |
| `xml` | XML/HTML — splits at element boundaries |

Each chunk is sized to fit within the model's context window alongside the system prompt and the continuity block. The completion budget (how many tokens the model can write back) is automatically calculated as a percentage of the input chunk size, with a generous minimum so reasoning-heavy models have room to think before outputting.

## Continuity

Between chunks, `cerebrate-file` builds a "continuity block": a sample of tokens from the tail of the previous chunk's input and a sample from the tail of its output. This gives the model just enough context to keep its voice and terminology consistent across chunks. The block is trimmed to fit the token budget if it would push the request over the context limit.

## CLI reference

```
cerebrate-file <input> [output] [options]

  --file-prompt PATH      Path to a file with system instructions
  --prompt TEXT           Freeform instructions appended to the system prompt
  --chunk-size INT        Target chunk size in tokens (from config if omitted)
  --max-tokens-ratio INT  Completion budget as % of chunk size (default: 150)
  --data-format TEXT      Chunking strategy: text|semantic|markdown|code|xml
  --sample-size INT       Tokens to carry forward as continuity context
  --temp FLOAT            Model temperature
  --top-p FLOAT           Nucleus sampling parameter
  --model TEXT            Model name override
  --verbose               Show per-chunk progress and token counts
  --explain               Parse YAML frontmatter and auto-generate missing fields
  --dry-run               Show chunk plan without making API calls
  --recurse GLOB          Process a directory tree matching GLOB pattern
  --workers INT           Parallel workers in recursive mode (default: 4)
  --force                 Overwrite existing output files
```

## Configuration

Settings load from three locations in order (later overrides earlier):

1. Built-in defaults (in the package)
2. `~/.config/cerebrate-file/config.toml`
3. `.cerebrate-file.toml` in the current directory

```toml
[inference]
model = "llama-4-scout-17b-16e-instruct"
chunk_size = 8000
max_tokens_ratio = 150
sample_size = 512
temperature = 0.3
top_p = 0.9
```

## Progressive output

Output is written to a temporary file and renamed atomically on completion. If the process is killed mid-run, the input file is untouched. In streaming mode (`--output -`), each processed chunk is written to stdout immediately so you can pipe it elsewhere.

## Cerebras context window

The Cerebras cloud API currently supports a 131,072 token context window. The tool enforces this limit before sending each request and raises an error if a chunk plus its system prompt would exceed it.

## License

MIT
