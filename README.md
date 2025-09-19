---
this_file: README.md
---
# cereproc.py

`old/cereproc.py` is a single-file utility that splits oversized documents into
Cerebras-friendly chunks, calls the `qwen-3-coder-480b` chat completion model
for each chunk, and stitches the results back together while keeping context
intact.

## Quick Start

```bash
export CEREBRAS_API_KEY="csk-..."
uv run old/cereproc.py --input_data document.md --output_data document.out.md
```

Add optional guidance by supplying an inline prompt or a separate instructions
file:

```bash
uv run old/cereproc.py \
  --input_data huge.md \
  --file_prompt prompts/style.md \
  --prompt "Write concise technical summaries." \
  --data_format code \
  --chunk_size 28000 \
  --sample_size 256 \
  --verbose
```

## CLI 

```
INFO: Showing help with the command 'cerebrate-file -- --help'.

NAME
    cerebrate-file - Process large documents by chunking for Cerebras qwen-3-coder-480b.

SYNOPSIS
    cerebrate-file INPUT_DATA <flags>

DESCRIPTION
    Process large documents by chunking for Cerebras qwen-3-coder-480b.

POSITIONAL ARGUMENTS
    INPUT_DATA
        Type: str
        Path to input file to process

FLAGS
    -o, --output_data=OUTPUT_DATA
        Type: Optional[Optional]
        Default: None
        Output file path (default: overwrite input_data)
    -f, --file_prompt=FILE_PROMPT
        Type: Optional[Optional]
        Default: None
        Path to file containing initial instructions
    -p, --prompt=PROMPT
        Type: Optional[Optional]
        Default: None
        Freeform instruction text to append after file_prompt
    -c, --chunk_size=CHUNK_SIZE
        Type: int
        Default: 32000
        Target maximum input chunk size in tokens (default: 32000)
    --max_tokens_ratio=MAX_TOKENS_RATIO
        Type: int
        Default: 100
        Completion budget as % of chunk size (default: 100)
    --data_format=DATA_FORMAT
        Type: str
        Default: 'markdown'
        Chunking strategy - text|semantic|markdown|code (default: markdown)
    -s, --sample_size=SAMPLE_SIZE
        Type: int
        Default: 200
        Number of tokens for continuity examples (default: 200)
    --temp=TEMP
        Type: float
        Default: 0.7
        Model temperature (default: 0.7)
    --top_p=TOP_P
        Type: float
        Default: 0.8
        Model top-p (default: 0.8)
    --model=MODEL
        Type: str
        Default: 'qwen-3-coder-480b'
        Model name override (default: qwen-3-coder-480b)
    -v, --verbose=VERBOSE
        Type: bool
        Default: False
        Enable debug logging (default: False)
    -e, --explain=EXPLAIN
        Type: bool
        Default: False
        Enable metadata processing with frontmatter parsing (default: False)
    --dry_run=DRY_RUN
        Type: bool
        Default: False
        Perform chunking and display results without making API calls (default: False)

NOTES
    You can also use flags syntax for POSITIONAL ARGUMENTS
```

## Processing Pipeline

1. Load `.env` values and validate `CEREBRAS_API_KEY` plus CLI arguments.
2. Build a base prompt from `--file_prompt` and `--prompt` (always separated by
   two newlines) and count its tokens.
3. Read the input file (frontmatter preserved) and optionally parse metadata
   when `--explain` is active.
4. Chunk the body using the selected strategy:
   - `text`: greedy line-based splitting.
   - `semantic`: paragraph-aware via `semantic-text-splitter`.
   - `markdown`: structure-aware Markdown splitter.
   - `code`: regex-guided boundaries for source files.
5. For each chunk, optionally blend in continuity examples drawn from the
   previous request/response pair (`--sample_size` tokens each way), truncated to
   stay within the 131K-token context budget.
6. Stream completions from Cerebras with adaptive rate-limit backoff and retry
   (`tenacity`) on transient failures.
7. Write the concatenated result atomically, preserving or updating frontmatter
   when `--explain` metadata is present.

## Explain Mode Metadata

When `--explain` is set, the script expects frontmatter containing
`title`, `author`, `id`, `type`, and `date`. Missing keys trigger a structured
JSON request to the model that fills only the absent values. Dry-run mode skips
this network call while still showing parsed metadata.

## Dry-Run Workflow

Use `--dry_run` to sanity-check chunk sizes, token budgets, and message shapes
without spending quota. The script prints the first two chunk envelopes, token
counts, and previews, then exits before creating the Cerebras client.

## Dependencies

Install requirements with `uv` (or your preferred tool):

- `fire`
- `loguru`
- `python-dotenv`
- `tenacity`
- `cerebras-cloud-sdk`
- `semantic-text-splitter`
- `qwen-tokenizer`
- `tqdm`
- `python-frontmatter`

## Environment

Set `CEREBRAS_API_KEY` before running. The utility warns on placeholder keys
and gently validates formatting. Use `--verbose` to surface additional runtime
information and rate-limit headers.

## Testing Tips

Run with `--dry_run` for fast validation, then process a short sample file in
`--verbose` mode to observe continuity handling and output statistics before you
launch against larger documents.
