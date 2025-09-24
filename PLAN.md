---
this_file: PLAN.md
---

# Issue 203 – STDIN/STDOUT Support for cerebrate-file CLI *(completed)*

## Problem Analysis
- The CLI currently assumes `input_data` and `output_data` are filesystem paths.
- Passing `-` (the Unix convention for stdin/stdout) causes validation and file I/O helpers to fail because they immediately coerce to `Path` objects.
- Users want to stream content through the tool in pipelines without touching intermediate files.

## Constraints
- Keep the implementation simple: reuse existing helpers rather than duplicating logic inside the CLI.
- Do not close or reassign `sys.stdin`/`sys.stdout`; avoid interfering with other tooling.
- Preserve existing behaviours for recursive mode; refuse combinations that do not make sense (e.g. `--recurse` with `input_data=-`).
- Maintain atomic file writes for real paths and keep current logging UX intact.
- Follow project rules: short functions, exhaustive tests, no new dependencies.

## Solution Options and Trade-offs
1. **Patch CLI only:** detect `-` inside `cli.run` and branch to bespoke read/write logic. (+) quick, (-) duplicates file handling, harder to test in isolation.
2. **Extend `read_file_safely`/`write_output_atomically`:** add stdin/stdout support inside shared utilities. (+) centralised behaviour, easier to test, (-) must carefully bypass Path logic. ✅
3. **Introduce new helper layer:** create dedicated stream helpers. (+) explicit semantics, (-) extra indirection and boilerplate without clear benefit.

## Edge Cases to Cover
- Empty stdin -> should produce empty output without errors.
- Using `--dry_run` or `--explain` together with stdin/stdout.
- Metadata/frontmatter generation when reading from stdin (should still work).
- `--output_data -` combined with existing file overwrite checks.
- Explicitly reject `--recurse` with `input_data=-` or `output_data=-` to avoid ambiguous semantics.

## Implementation Phases
1. **Utility Enhancements**
   - Update `read_file_safely` to return `sys.stdin.read()` when given `-`.
   - Update `write_output_atomically` to stream to `sys.stdout.write()` when the target is `-`, skipping temp-file logic.
   - Ensure logging remains informative (include markers when using streams).

2. **Validation Adjustments**
   - Teach `validate_inputs` to accept `-` without touching the filesystem, while keeping other checks intact.
   - Guard recursive validation: raise/exit if stdin/stdout markers are used with `--recurse`.

3. **CLI Integration**
   - Skip path existence checks and overwrite warnings when dealing with stdout.
   - Ensure base prompt and frontmatter handling work identically for streamed input/output.
   - Prevent progress displays or summaries from corrupting stdout output when streaming (e.g. flush output after processing, document behaviour).

4. **Testing & Documentation**
   - Add unit tests for the updated utilities using `io.StringIO` + monkeypatching.
   - Add CLI-level test (or high-level function test) to verify stdin→stdout round-trip with simple content.
   - Update README usage examples plus CHANGELOG/TODO/WORK as required.

## Testing Strategy
- Unit tests for `read_file_safely` and `write_output_atomically` covering both path and `-` inputs.
- Integration-style test invoking `cli.run` with mocked stdin/stdout to confirm pipeline behaviour.
- Re-run full test suite (`python -m pytest -xvs`).

## Dependencies
- No new packages; rely on `sys` and `io` from the standard library.

## Future Considerations
- Could add support for piping multiple files via archive formats if demand arises, but out of scope now.
- Consider configurable separators when streaming multiple files in the future, if recursive + stdout support becomes a requirement.

## Completion Summary
- Implementation merged with tests and documentation updates on 2025-09-24.
- Streaming markers rejected in recursive mode to prevent ambiguous batch semantics.
- README and CHANGELOG refreshed with usage guidance.
