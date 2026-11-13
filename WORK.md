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

## 2026-10-06: writing comparison adapter

Added compatible.py and seven response-boundary tests. Baseline: 224 passed, three force-option failures caused by wrong mock targets and archived live model. Fixed imported CLI mock targets; full suite: 234 passed in 4.01s. CLI constructors in other tests still produce TCP warming requests; strict network isolation remains to verify.

## 2026-11-13: askllm2 backend

- Added explicit `--provider askllm2` routing for FreeLLM default chain and `poe:<bot>`, preserving Cerebras as the default. Document data goes through stdin, chunk failures abort, and file destinations use atomic replacement.
- Live FreeLLM default-chain and Poe Gemma CLI smoke tests on disposable `The sky are blue.` both produced `The sky is blue.`.
- Verification: full Python 3.12 test suite 240 passed; subsequent targeted suite 8 passed (two additional tests added after the full run); targeted Ruff and mypy clean. Existing legacy tests still issue Cerebras TCP warming requests. Initial Python 3.14 setup failed because locked tiktoken PyO3 supports up to 3.13; Python 3.12 succeeded.
- Independent review fixes: preserve chat roles via `--messages -`, fail closed on metadata errors, report recursive failures via nonzero exit, and restrict generated metadata to missing fields. Full suite: 247 passed; targeted Ruff and mypy clean. Live FreeLLM and Poe document transforms repeated after role-preserving changes and both succeeded.

## 2026-11-13: release verification

- Published 1.0.38 with audited wheel and source distribution; their PyPI SHA-256 digests match the locally audited artifacts. Installed both artifacts and the PyPI release in isolated Python 3.12 environments; a FreeLLM library call succeeded.
- The exact release checkout passed 253 tests on Python 3.10, 3.11, and 3.12 using a synthetic Cerebras credential. The release workflow's trusted-publisher exchange failed; the audited artifacts were published directly and attached to the GitHub release.
- Corrected pre-existing Ruff formatting issues in three Markdown files and supplied a synthetic test-only Cerebras credential in CI. The real Cerebras inference path remains unverified because the available credential returned HTTP 401.
