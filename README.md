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

## CLI Flags

- `--input_data PATH` (required) Text/Markdown/code file to process.
- `--output_data PATH` Destination file (defaults to the input path).
- `--file_prompt PATH` Load reusable instructions; appended before the inline prompt.
- `--prompt TEXT` Freeform instructions appended after the file prompt.
- `--chunk_size INT` Target chunk size in tokens (default `32000`).
- `--data_format text|semantic|markdown|code` Chunking strategy (default `markdown`).
- `--sample_size INT` Continuity example size in tokens (default `200`, use `0` to disable).
- `--max_tokens_ratio INT` Completion budget as `%` of chunk tokens (default `100`).
- `--temp FLOAT` and `--top_p FLOAT` Sampling controls (defaults `0.7` / `0.8`).
- `--model TEXT` Cerebras model name override (default `qwen-3-coder-480b`).
- `--verbose` Enable detailed logging and chunk previews.
- `--dry_run` Inspect chunking and request envelopes without calling the API.
- `--explain` Parse Markdown frontmatter, ensure required metadata fields, and
  ask the model to fill gaps before processing.

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
