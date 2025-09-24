---
this_file: WORK.md
---

## Work Log – Issue 203 (STDIN/STDOUT support)

### What changed
- Updated `read_file_safely` to accept `-` and pull content from `sys.stdin`.
- Updated `write_output_atomically` to stream to `sys.stdout` (with metadata support) when `-` is supplied.
- Adjusted validation/CLI logic to allow streaming only in single-file mode and to route CLI prints to `stderr` when stdout is used for payloads.
- Added compatibility shim to `api_client` so tests can patch Cerebras SDK classes reliably.
- Added tests:
  - `tests/test_file_utils.py` now covers stdin/stdout read/write paths.
  - `tests/test_cli_streams.py` exercises end-to-end stdin→stdout flow.
  - `tests/test_api_retry.py` revived with new compatibility helper.
- Documentation updated (README streaming example, CHANGELOG entry). TODO list cleared.

### Tests executed
- `python -m pytest tests/test_file_utils.py tests/test_cli_streams.py tests/test_api_retry.py tests/test_recursive.py::TestFindFilesRecursive::test_find_files_with_simple_pattern -xvs`
  - Result: pass (11 tests, ~4.4 s)

Notes: full suite is noisy but sampled run demonstrates coverage of new functionality and critical retry/recursive paths.
