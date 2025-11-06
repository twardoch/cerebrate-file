Here's a revised version of your `README.md` with tighter prose, clearer structure, and minimal fluff. I've preserved all essential information while improving readability and precision.

---

# cereproc.py

`old/cereproc.py` processes large documents by splitting them into chunks suitable for the Cerebras `zai-glm-4.6` model, generating completions for each chunk, and reassembling the results while maintaining context.

## Quick Start

```bash
export CEREBRAS_API_KEY="csk-..."
uv run old/cereproc.py --input_data document.md --output_data document.out.md
```

Add optional guidance using inline prompts or instruction files:

```bash
uv run old/cereproc.py \
  --input_data huge.md \
  --file_prompt prompts/style.md \
  --prompt "Write concise technical summaries." \
  -c code \
  --chunk_size 28000 \
  --sample_size 256 \
  --verbose
```

## CLI

```
NAME
    cerebrate-file - Process large documents by chunking for Cerebras zai-glm-4.6

SYNOPSIS
    cerebrate-file INPUT_DATA <flags>

POSITIONAL ARGUMENTS
    INPUT_DATA
        Path to input file to process

FLAGS
    -o, --output_data=OUTPUT_DATA
        Output file path (default: overwrite input)
    -f, --file_prompt=FILE_PROMPT
        Path to file with initial instructions
    -p, --prompt=PROMPT
        Inline prompt text (appended after file_prompt)
    -c, --chunk_size=CHUNK_SIZE
        Target max chunk size in tokens (default: 32000)
    --max_tokens_ratio=MAX_TOKENS_RATIO
        Completion budget as % of chunk size (default: 100)
    --data_format=DATA_FORMAT
        Chunking strategy: text | semantic | markdown | code (default: markdown)
    -s, --sample_size=SAMPLE_SIZE
        Tokens from previous request/response to maintain context (default: 200)
    --temp=TEMP
        Model temperature (default: 0.7)
    --top_p=TOP_P
        Model top-p sampling (default: 0.8)
    --model=MODEL
        Override default model name (default: zai-glm-4.6)
    -v, --verbose
        Enable debug logging
    -e, --explain
        Parse and update frontmatter metadata
    --dry_run
        Show chunking details without calling the API
```

### Streaming via STDIN/STDOUT

Use `-` to read from stdin or write to stdout:

```bash
cat huge.md | uv run cerebrate_file --input_data - --output_data - > processed.md
```

## Processing Pipeline

1. Load `.env` and validate `CEREBRAS_API_KEY` and CLI arguments.
2. Construct base prompt from `--file_prompt` and `--prompt`, separated by two newlines. Count its tokens.
3. Read input file, preserving frontmatter. Parse metadata if `--explain` is enabled.
4. Split document body using one of these strategies:
   - `text`: line-based greedy splitting
   - `semantic`: paragraph-aware via `semantic-text-splitter`
   - `markdown`: structure-preserving Markdown splitting
   - `code`: regex-based source code boundaries
5. For each chunk, optionally prepend/append continuity examples (`--sample_size` tokens each) from prior interactions, ensuring total tokens stay under the 131K limit.
6. Stream responses from Cerebras, with automatic retry and backoff on transient errors (`tenacity`).
7. Write final output atomically. Update frontmatter if `--explain` is active.

## Explain Mode Metadata

When `--explain` is set, the script looks for frontmatter containing:

- `title`
- `author`
- `id`
- `type`
- `date`

Missing fields are filled via a structured JSON query to the model. Use `--dry_run` to preview parsed metadata without making network calls.

## Dry Run Workflow

Use `--dry_run` to inspect:
- Chunk sizes
- Token budgets
- Message structure

No API calls are made in this mode.

## Dependencies

Install with `uv` or your preferred package manager:

- `fire`
- `loguru`
- `python-dotenv`
- `tenacity`
- `cerebras-cloud-sdk`
- `semantic-text-splitter`
- `qwen-tokenizer`
- `tqdm`
- `python-frontmatter`

## Environment Setup

Set `CEREBRAS_API_KEY` before running. The tool will warn about placeholder keys and validate basic formatting. Use `--verbose` for extra runtime info and rate-limit headers.

## Testing Tips

1. Run with `--dry_run` to check chunking logic quickly.
2. Test on a small sample file with `--verbose` to observe:
   - Context blending between chunks
   - Output statistics
3. Only then run on larger inputs.

--- 

Let me know if you'd like this tailored further toward users, developers, or integration into a larger documentation system.