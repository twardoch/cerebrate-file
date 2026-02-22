#!/usr/bin/env python3
# this_file: tests/test_recursive.py

"""Tests for recursive file processing in cerebrate_file package."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cerebrate_file.models import ProcessingState
from cerebrate_file.recursive import (
    ProcessingResult,
    _load_gitignore_spec,
    find_files_recursive,
    process_files_parallel,
    process_single_file,
    replicate_directory_structure,
)


class TestFindFilesRecursive:
    """Test find_files_recursive function."""

    def test_find_files_with_simple_pattern(self):
        """Test finding files with a simple pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create test file structure
            (tmp_path / "file1.md").write_text("content1")
            (tmp_path / "file2.md").write_text("content2")
            (tmp_path / "file3.txt").write_text("content3")
            (tmp_path / "subdir").mkdir()
            (tmp_path / "subdir" / "file4.md").write_text("content4")

            # Find .md files
            result = find_files_recursive(tmp_path, "*.md", None)

            # Note: rglob("*.md") actually finds all .md files recursively
            assert len(result) == 3
            input_files = [str(p[0].name) for p in result]
            assert "file1.md" in input_files
            assert "file2.md" in input_files
            assert "file4.md" in input_files

    def test_find_files_with_recursive_pattern(self):
        """Test finding files with recursive pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create test file structure
            (tmp_path / "file1.md").write_text("content1")
            (tmp_path / "subdir").mkdir()
            (tmp_path / "subdir" / "file2.md").write_text("content2")
            (tmp_path / "subdir" / "deep").mkdir()
            (tmp_path / "subdir" / "deep" / "file3.md").write_text("content3")

            # Find all .md files recursively
            result = find_files_recursive(tmp_path, "**/*.md", None)

            # Should find all .md files
            assert len(result) == 3
            input_files = [p[0].name for p in result]
            assert "file1.md" in input_files
            assert "file2.md" in input_files
            assert "file3.md" in input_files

    def test_find_files_with_output_directory(self):
        """Test finding files and generating output paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / "output"

            input_dir.mkdir()
            output_dir.mkdir()

            # Create test files
            (input_dir / "file1.md").write_text("content1")
            (input_dir / "subdir").mkdir()
            (input_dir / "subdir" / "file2.md").write_text("content2")

            # Find files with output directory
            result = find_files_recursive(input_dir, "**/*.md", output_dir)

            assert len(result) == 2
            # Check output paths maintain directory structure
            for input_path, output_path in result:
                relative = input_path.relative_to(input_dir.resolve())
                expected_output = output_dir.resolve() / relative
                assert output_path == expected_output

    def test_find_files_no_matches(self):
        """Test finding files when no matches exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create only .txt files
            (tmp_path / "file1.txt").write_text("content1")

            # Try to find .md files
            result = find_files_recursive(tmp_path, "*.md", None)

            assert len(result) == 0

    def test_find_files_nonexistent_directory(self):
        """Test error when directory doesn't exist."""
        with pytest.raises(ValueError, match="does not exist"):
            find_files_recursive(Path("/nonexistent/path"), "*.md", None)

    def test_find_files_not_directory(self):
        """Test error when path is not a directory."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            tmp_path = Path(tmpfile.name)

            with pytest.raises(ValueError, match="not a directory"):
                find_files_recursive(tmp_path, "*.md", None)


class TestReplicateDirectoryStructure:
    """Test replicate_directory_structure function."""

    def test_replicate_simple_structure(self):
        """Test replicating a simple directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            output_dir = tmp_path / "output"

            # Create file pairs
            file_pairs = [
                (Path("input/file1.txt"), output_dir / "file1.txt"),
                (Path("input/subdir/file2.txt"), output_dir / "subdir" / "file2.txt"),
            ]

            # Replicate structure
            replicate_directory_structure(file_pairs)

            # Check directories were created
            assert output_dir.exists()
            assert (output_dir / "subdir").exists()

    def test_replicate_existing_directories(self):
        """Test replicating when directories already exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            output_dir = tmp_path / "output"

            # Pre-create some directories
            output_dir.mkdir()
            (output_dir / "existing").mkdir()

            # Create file pairs
            file_pairs = [
                (Path("input/file1.txt"), output_dir / "file1.txt"),
                (Path("input/existing/file2.txt"), output_dir / "existing" / "file2.txt"),
            ]

            # Should not fail even if directories exist
            replicate_directory_structure(file_pairs)

            assert output_dir.exists()
            assert (output_dir / "existing").exists()

    def test_replicate_empty_list(self):
        """Test replicating with empty file list."""
        # Should not fail with empty list
        replicate_directory_structure([])


class TestProcessSingleFile:
    """Test process_single_file function."""

    def test_process_successful(self):
        """Test successful file processing."""
        input_path = Path("input.txt")
        output_path = Path("output.txt")

        # Mock processing function
        state = ProcessingState()
        state.total_output_tokens = 100
        processing_func = Mock(return_value=state)

        # Mock progress callback
        progress_callback = Mock()

        # Process file
        result = process_single_file(input_path, output_path, processing_func, progress_callback)

        assert result[0] == input_path
        assert result[1] == output_path
        assert result[2] == state
        assert result[3] is None  # No exception

        processing_func.assert_called_once_with(input_path, output_path)
        progress_callback.assert_called_once_with(str(input_path), 1)

    def test_process_with_exception(self):
        """Test file processing with exception."""
        input_path = Path("input.txt")
        output_path = Path("output.txt")

        # Mock processing function that raises exception
        processing_func = Mock(side_effect=RuntimeError("Processing failed"))

        # Process file
        result = process_single_file(input_path, output_path, processing_func, None)

        assert result[0] == input_path
        assert result[1] == output_path
        assert isinstance(result[2], ProcessingState)
        assert isinstance(result[3], RuntimeError)


class TestProcessFilesParallel:
    """Test process_files_parallel function."""

    def test_parallel_processing_success(self):
        """Test successful parallel processing."""
        # Create file pairs
        file_pairs = [
            (Path("input1.txt"), Path("output1.txt")),
            (Path("input2.txt"), Path("output2.txt")),
        ]

        # Mock processing function
        def mock_process(input_path: Path, output_path: Path):
            state = ProcessingState()
            state.total_input_tokens = 50
            state.total_output_tokens = 100
            state.processing_time = 1.0
            return state

        # Process files
        result = process_files_parallel(file_pairs, mock_process, workers=2)

        assert len(result.successful) == 2
        assert len(result.failed) == 0
        assert result.total_input_tokens == 100  # 50 * 2
        assert result.total_output_tokens == 200  # 100 * 2
        assert result.total_time == 2.0  # 1.0 * 2

    def test_parallel_processing_with_failures(self):
        """Test parallel processing with some failures."""
        # Create file pairs
        file_pairs = [
            (Path("input1.txt"), Path("output1.txt")),
            (Path("input2.txt"), Path("output2.txt")),
            (Path("input3.txt"), Path("output3.txt")),
        ]

        # Mock processing function that fails for input2.txt
        def mock_process(input_path: Path, output_path: Path):
            if "input2" in str(input_path):
                raise RuntimeError("Failed to process")

            state = ProcessingState()
            state.total_input_tokens = 50
            state.total_output_tokens = 100
            state.processing_time = 1.0
            return state

        # Process files
        result = process_files_parallel(file_pairs, mock_process, workers=2)

        assert len(result.successful) == 2
        assert len(result.failed) == 1
        assert result.total_input_tokens == 100  # 50 * 2 (successful)
        assert result.total_output_tokens == 200  # 100 * 2 (successful)
        assert "Failed to process" in str(result.failed[0][1])

    def test_parallel_processing_empty_list(self):
        """Test parallel processing with empty file list."""
        result = process_files_parallel([], Mock(), workers=2)

        assert len(result.successful) == 0
        assert len(result.failed) == 0
        assert result.total_input_tokens == 0
        assert result.total_output_tokens == 0

    def test_parallel_processing_with_progress(self):
        """Test parallel processing with progress callback."""
        file_pairs = [
            (Path("input1.txt"), Path("output1.txt")),
        ]

        def mock_process(input_path: Path, output_path: Path):
            return ProcessingState()

        progress_callback = Mock()

        # Process files
        process_files_parallel(
            file_pairs, mock_process, workers=1, progress_callback=progress_callback
        )

        # Progress callback should be called
        progress_callback.assert_called()


class TestProcessingResult:
    """Test ProcessingResult class."""

    def test_initialization(self):
        """Test ProcessingResult initialization."""
        result = ProcessingResult()

        assert result.successful == []
        assert result.failed == []
        assert result.total_input_tokens == 0
        assert result.total_output_tokens == 0
        assert result.total_time == 0.0


class TestRecursiveIntegration:
    """Integration tests for recursive processing."""

    @patch("cerebrate_file.recursive.ThreadPoolExecutor")
    def test_full_recursive_workflow(self, mock_executor):
        """Test complete recursive processing workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_dir = tmp_path / "input"
            output_dir = tmp_path / "output"

            input_dir.mkdir()

            # Create test files
            (input_dir / "file1.md").write_text("content1")
            (input_dir / "subdir").mkdir()
            (input_dir / "subdir" / "file2.md").write_text("content2")

            # Find files
            file_pairs = find_files_recursive(input_dir, "**/*.md", output_dir)
            assert len(file_pairs) == 2

            # Replicate structure
            replicate_directory_structure(file_pairs)
            assert output_dir.exists()
            assert (output_dir / "subdir").exists()

            # Mock executor for parallel processing
            mock_executor_instance = MagicMock()
            mock_executor.return_value.__enter__.return_value = mock_executor_instance
            mock_executor_instance.submit.return_value.result.return_value = (
                Path("input"),
                Path("output"),
                ProcessingState(),
                None,
            )

            # Process files (mocked)
            def mock_process(input_path: Path, output_path: Path):
                return ProcessingState()

            process_files_parallel(file_pairs, mock_process, workers=2)

            # Verify executor was used
            mock_executor.assert_called_once_with(max_workers=2)


class TestLoadGitignoreSpec:
    """Tests for _load_gitignore_spec helper."""

    def test_no_gitignore(self):
        """Returns None when no .gitignore exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = _load_gitignore_spec(Path(tmpdir))
            assert result is None

    def test_single_gitignore(self):
        """Loads patterns from a single .gitignore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / ".gitignore").write_text("*.log\nbuild/\n")
            # Create .git dir so traversal stops here
            (tmp_path / ".git").mkdir()

            spec = _load_gitignore_spec(tmp_path)
            assert spec is not None
            assert spec.match_file("app.log")
            assert spec.match_file("build/output.js")
            assert not spec.match_file("src/main.py")

    def test_stops_at_git_boundary(self):
        """Stops walking at .git directory, not beyond."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            repo_root = tmp_path / "repo"
            repo_root.mkdir()
            (repo_root / ".git").mkdir()
            (repo_root / ".gitignore").write_text("*.pyc\n")

            # Place another .gitignore ABOVE the repo root
            (tmp_path / ".gitignore").write_text("*.secret\n")

            subdir = repo_root / "src"
            subdir.mkdir()

            spec = _load_gitignore_spec(subdir)
            assert spec is not None
            # Should include repo-root .gitignore
            assert spec.match_file("foo.pyc")
            # Should NOT include the one above .git
            assert not spec.match_file("foo.secret")

    def test_nested_gitignore_precedence(self):
        """Deeper .gitignore patterns override shallower ones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / ".git").mkdir()
            (tmp_path / ".gitignore").write_text("*.log\n")

            subdir = tmp_path / "sub"
            subdir.mkdir()
            # Negate *.log in deeper gitignore
            (subdir / ".gitignore").write_text("!*.log\n")

            spec = _load_gitignore_spec(subdir)
            assert spec is not None
            # After reading root then sub, the negation should apply
            assert not spec.match_file("debug.log")


class TestGitignoreFiltering:
    """Tests for .gitignore filtering in find_files_recursive."""

    def test_gitignore_excludes_matching_files(self):
        """Files matching .gitignore patterns are excluded by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / ".git").mkdir()
            (tmp_path / ".gitignore").write_text("*.log\nbuild/\n")

            # Create files — some should be ignored
            (tmp_path / "main.py").write_text("code")
            (tmp_path / "debug.log").write_text("log")
            (tmp_path / "build").mkdir()
            (tmp_path / "build" / "output.js").write_text("built")

            result = find_files_recursive(tmp_path, "*", None)
            result_names = {p[0].name for p in result}

            assert "main.py" in result_names
            assert "debug.log" not in result_names
            assert "output.js" not in result_names

    def test_unrestricted_includes_all_files(self):
        """With unrestricted=True, .gitignore patterns are not applied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / ".git").mkdir()
            (tmp_path / ".gitignore").write_text("*.log\n")

            (tmp_path / "main.py").write_text("code")
            (tmp_path / "debug.log").write_text("log")

            result = find_files_recursive(tmp_path, "*", None, unrestricted=True)
            result_names = {p[0].name for p in result}

            assert "main.py" in result_names
            assert "debug.log" in result_names

    def test_no_gitignore_passes_all_files(self):
        """Without a .gitignore, all files pass through even with filtering on."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            (tmp_path / "file1.md").write_text("a")
            (tmp_path / "file2.txt").write_text("b")

            result = find_files_recursive(tmp_path, "*", None)
            assert len(result) == 2

    def test_all_files_filtered_returns_empty(self):
        """Returns empty list with warning when all files are filtered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / ".git").mkdir()
            (tmp_path / ".gitignore").write_text("*.md\n")

            (tmp_path / "readme.md").write_text("hi")

            result = find_files_recursive(tmp_path, "*.md", None)
            assert result == []

    def test_gitignore_with_output_dir(self):
        """Gitignore filtering works correctly with output directory mapping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            input_dir = tmp_path / "in"
            output_dir = tmp_path / "out"
            input_dir.mkdir()
            output_dir.mkdir()
            (input_dir / ".git").mkdir()
            (input_dir / ".gitignore").write_text("*.log\n")

            (input_dir / "code.py").write_text("x")
            (input_dir / "app.log").write_text("y")

            result = find_files_recursive(input_dir, "*", output_dir)
            result_names = {p[0].name for p in result}
            # .gitignore itself is not excluded by its own patterns,
            # so we get .gitignore + code.py (app.log is filtered)
            assert "code.py" in result_names
            assert "app.log" not in result_names
            # Verify output mapping for code.py
            code_pairs = [p for p in result if p[0].name == "code.py"]
            assert len(code_pairs) == 1
            assert code_pairs[0][1] == output_dir.resolve() / "code.py"

    def test_existing_tests_unaffected_by_default_param(self):
        """Existing call-sites without unrestricted still work (keyword default)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "file.md").write_text("ok")

            # Call without unrestricted — should default to False
            result = find_files_recursive(tmp_path, "*.md", None)
            assert len(result) == 1


class TestGitDirExclusion:
    """Tests that .git directories are ALWAYS excluded, even with --unrestricted."""

    def test_git_dir_excluded_by_default(self):
        """Files inside .git/ are excluded in normal (restricted) mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / ".git").mkdir()
            (tmp_path / ".git" / "config").write_text("[core]")
            (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main")
            (tmp_path / "real_file.py").write_text("print('hello')")

            result = find_files_recursive(tmp_path, "*", None)
            result_names = {p[0].name for p in result}

            assert "real_file.py" in result_names
            assert "config" not in result_names
            assert "HEAD" not in result_names

    def test_git_dir_excluded_with_unrestricted(self):
        """Files inside .git/ are excluded even when unrestricted=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / ".git").mkdir()
            (tmp_path / ".git" / "config").write_text("[core]")
            (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main")
            (tmp_path / ".git" / "objects").mkdir()
            (tmp_path / ".git" / "objects" / "pack").mkdir()
            (tmp_path / ".git" / "objects" / "pack" / "data.pack").write_text("binary")
            (tmp_path / "real_file.py").write_text("print('hello')")
            (tmp_path / "debug.log").write_text("log entry")

            result = find_files_recursive(tmp_path, "*", None, unrestricted=True)
            result_names = {p[0].name for p in result}

            # All non-.git files should be present (unrestricted skips gitignore)
            assert "real_file.py" in result_names
            assert "debug.log" in result_names
            # .git contents must NEVER appear
            assert "config" not in result_names
            assert "HEAD" not in result_names
            assert "data.pack" not in result_names

    def test_git_dir_nested_excluded(self):
        """.git inside a subdirectory (e.g. submodule) is also excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            submodule = tmp_path / "vendor" / "lib"
            submodule.mkdir(parents=True)
            (submodule / ".git").mkdir()
            (submodule / ".git" / "HEAD").write_text("ref: refs/heads/main")
            (submodule / "lib.py").write_text("code")
            (tmp_path / "main.py").write_text("import vendor")

            result = find_files_recursive(tmp_path, "*", None, unrestricted=True)
            result_names = {p[0].name for p in result}

            assert "main.py" in result_names
            assert "lib.py" in result_names
            assert "HEAD" not in result_names
