---
this_file: PLAN.md
---

# Cerebrate-File: Refinement and Stabilization Plan

This plan outlines two main objectives: first, to diagnose and fix the critical "zero-token output" bug, and second, to perform a comprehensive cleanup of the repository to improve maintainability, clarity, and adherence to best practices.

---

## Phase 1: Bug Fix — Resolve Zero-Token Output (Issue #204)

The highest priority is to fix the bug where `cerebrate-file` fails with "zero tokens returned" for each chunk, while the simpler `testapi.py` script successfully processes a whole file. This indicates a problem in the main tool's chunking or request logic, not the Cerebras API itself.

### 1.1. Problem Analysis

- **Symptom:** The tool produces "Chunk X returned zero tokens" warnings for all chunks and aborts, leaving the output file empty.
- **Clue:** `testapi.py` sends the entire file in one request and succeeds. `cerebrate-file` fails when it splits the same file into chunks.
- **Hypothesis:** The issue likely lies in one of these areas:
    1.  **Chunk Content:** The chunking logic might be creating malformed or empty chunks.
    2.  **Request Parameters:** The `max_completion_tokens` for each chunk might be calculated incorrectly (e.g., as zero or a negative number).
    3.  **API Changes:** The Cerebras API may have new requirements for chunked requests that the tool doesn't meet. The successful `testapi.py` uses `zai-glm-4.6`, while the failing `cerebrate-file` log also shows `zai-glm-4.6`. The model seems consistent.

### 1.2. Investigation and Debugging Strategy

1.  **Reproduce the Failure:** Run the exact command from `issues/204.md`:
    ```bash
    cerebrate-file -i CHANGELOG.md -o CHANGELOG2.md -c 1024 -p "Slightly compress this CHANGELOG: only keep relevant facts, eliminate fluff"
    ```
2.  **Add Debug Logging:** Enhance the logging in `cerebrate_file/cerebrate_file.py` and `cerebrate_file/api_client.py` to print the exact content and parameters of each chunk's API request just before it's sent. Key information to log:
    -   Chunk content being sent.
    -   `max_completion_tokens` value.
    -   The full `messages` payload.
3.  **Analyze and Fix:**
    -   Examine the logged output to find the discrepancy. Is the content empty? Is `max_completion_tokens` too small or invalid?
    -   Modify the chunking or token calculation logic based on the findings.
    -   Iteratively test the fix until the command succeeds and `CHANGELOG2.md` is generated correctly.
4.  **Create a Regression Test:** Add a new test case to `tests/test_cerebrate_file.py` that specifically replicates this failure condition (e.g., processing a small file with small chunks) to ensure it doesn't happen again.

---

## Phase 2: Repository Cleanup and Standardization

After the bug is fixed and the tool is stable, we will clean up the repository.

### 2.1. File Consolidation and Deletion

-   **Objective:** Eliminate redundant, temporary, and obsolete files.
-   **Actions:**
    1.  **Merge `CHANGELOG.md` and `CHANGELOG2.md`:** Consolidate all relevant, project-specific history into `CHANGELOG.md` and delete `CHANGELOG2.md`. The format should follow the "Keep a Changelog" standard.
    2.  **Consolidate Development Guidelines:** Merge `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `LLXPRT.md`, `QWEN.md`, and `.cursorrules` into a single, comprehensive `CONTRIBUTING.md`. This file will serve as the single source of truth for development process and agent instructions.
    3.  **Remove Obsolete Scripts:**
        -   Delete `package.toml` (unused).
        -   Delete `test_retry_mechanism.py` after merging its logic into a new integration test in `tests/test_api_retry.py`.
        -   Delete `test1.sh` and `test2.sh` (obsolete).
    4.  **Archive or Remove One-off Files:**
        -   Delete `REVIEW.md` (insights can be moved to docs if needed).
        -   Delete `issues/204.md` once the bug is fixed and documented in the changelog.
        -   Delete temporary files like `md.txt`.

### 2.2. Documentation and Configuration Overhaul

-   **Objective:** Make the project easy to understand, use, and contribute to.
-   **Actions:**
    1.  **Update `README.md`:** Rewrite the README to be a concise, welcoming entry point. It should briefly describe the project, show a clear usage example, and link to the full documentation in the `docs/` directory. Remove references to `old/cereproc.py`.
    2.  **Standardize Scripts:** Review `build.sh`. Move its core logic into `pyproject.toml` as `hatch` scripts for consistency (`hatch run build`, `hatch run publish`, etc.). Document the release process in `CONTRIBUTING.md`.
    3.  **Clean `TODO.md` and `WORK.md`:** Clear the completed tasks from these files to prepare for the next development cycle.
    4.  **Centralize Configuration:** Ensure `pyproject.toml` remains the single source of truth for all project configuration (dependencies, linting, testing, building).

### 2.3. Final Polish

-   **Objective:** Ensure the repository follows Python community best practices.
-   **Actions:**
    1.  **Add Standard Files:** Consider adding a `CODE_OF_CONDUCT.md`.
    2.  **Review `.gitignore`:** Ensure all generated files and artifacts are ignored.
    3.  **Run Full Test Suite:** After all changes, run the entire test suite (`uvx hatch test`) to confirm that nothing has been broken during the cleanup.