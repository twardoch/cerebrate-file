---
this_file: TODO.md
---

- [x] Teach `read_file_safely` to read from stdin when path is `-`
- [x] Allow `write_output_atomically` to stream to stdout when output path is `-`
- [x] Relax input validation to accept stdin/stdout markers while rejecting invalid recursive combos
- [x] Update CLI overwrite logic and messaging for streamed input/output
- [x] Add unit tests covering stdin/stdout helpers
- [x] Add integration-style test for CLI stdin→stdout flow
- [x] Refresh README/CHANGELOG/WORK notes with the new behaviour
- [x] Emit chunk-level diagnostics whenever the API returns zero tokens
- [x] Abort CLI writes if the combined output tokens are zero and show API request details
- [x] Cover the zero-output safeguards with regression tests and documentation updates
