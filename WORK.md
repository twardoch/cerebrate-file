# this_file: WORK.md

Current iteration scratchpad. Clean after each sprint.

## Active Work

_(empty - ready for next sprint)_

## Notes

Last sprint completed (2026-07-05 modernization):
- ruff/format/mypy clean across src + tests; real bugs fixed in cli.py (None rate-status guard, progress-display type collision) and api_client.py
- Test suite fully offline and green (227 passed): rewrote test_full_retry_flow to mock fallbacks, fixed macOS path test, replaced hanging MagicMock executor with real Futures
- Added pytest-mock + pytest-timeout to test extra; added project icon

Prior sprint:
- Progressive file writing with .tmptmp temp file support
- Model update from zai-glm-4.6 to zai-glm-4.7
- Cleanup of obsolete files (test_retry_mechanism.py, issues/, md.txt)
- Test fix for chunk_writer callback mocking
