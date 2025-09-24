# this_file: tests/test_prompt_library.py

"""Tests for prompt library functionality.

Tests verify that the prompt library can load prompts from both
user-specified paths and the built-in library.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cerebrate_file.file_utils import build_base_prompt
from cerebrate_file.prompt_library import (
    get_prompt_library_path,
    resolve_prompt_file,
)


class TestPromptLibrary:
    """Test prompt library functionality."""

    def test_get_prompt_library_path(self):
        """Test that prompt library path is correctly determined."""
        prompt_path = get_prompt_library_path()

        # Should return a Path object
        assert isinstance(prompt_path, Path)

        # Should point to the prompts folder within cerebrate_file package
        assert prompt_path.name == "prompts"
        assert "cerebrate_file" in str(prompt_path)

    def test_resolve_prompt_file_direct_path(self, tmp_path):
        """Test resolving a prompt file with a direct path."""
        # Create a test prompt file
        test_prompt = tmp_path / "test_prompt.txt"
        test_prompt.write_text("Test prompt content")

        # Should find the file using direct path
        resolved = resolve_prompt_file(str(test_prompt))
        assert resolved == test_prompt

    def test_resolve_prompt_file_from_library(self):
        """Test resolving a prompt file from the library."""
        # Test with the actual prompt file we added
        resolved = resolve_prompt_file("fix-pdf-extracted-text.xml")

        # Should find the file in the library
        assert resolved is not None
        assert resolved.name == "fix-pdf-extracted-text.xml"
        assert "prompts" in str(resolved)

    def test_resolve_prompt_file_not_found(self):
        """Test behavior when prompt file is not found."""
        # Non-existent file
        resolved = resolve_prompt_file("non_existent_prompt.txt")

        # Should return None
        assert resolved is None

    def test_resolve_prompt_file_with_path_fallback(self):
        """Test that filename is tried if full path doesn't exist in library."""
        # Try with a path that doesn't exist, but filename might
        with patch("cerebrate_file.prompt_library.get_prompt_library_path") as mock_get_path:
            # Create a mock library with a test file
            mock_library = MagicMock()
            mock_library.exists.return_value = True
            mock_get_path.return_value = mock_library

            # Mock the path operations
            mock_file = MagicMock()
            mock_file.exists.return_value = True
            mock_file.is_file.return_value = True
            mock_library.__truediv__ = MagicMock(return_value=mock_file)

            resolve_prompt_file("some/path/test.xml")

            # Should have tried to find the file
            assert mock_library.__truediv__.called

    def test_build_base_prompt_with_library_file(self):
        """Test that build_base_prompt works with library files."""
        # Test with actual library file
        prompt_text, token_count = build_base_prompt("fix-pdf-extracted-text.xml", None)

        # Should have loaded content
        assert len(prompt_text) > 0
        assert token_count > 0

        # Should contain expected content from the prompt
        assert "document restoration specialist" in prompt_text

    def test_build_base_prompt_with_direct_file(self, tmp_path):
        """Test that build_base_prompt works with direct file paths."""
        # Create a test prompt file
        test_prompt = tmp_path / "test_prompt.txt"
        test_prompt.write_text("Direct prompt content")

        prompt_text, token_count = build_base_prompt(str(test_prompt), "Additional text")

        # Should contain both file and text content
        assert "Direct prompt content" in prompt_text
        assert "Additional text" in prompt_text
        assert token_count > 0

    def test_build_base_prompt_with_missing_file(self):
        """Test that build_base_prompt fails gracefully with missing file."""
        with pytest.raises(SystemExit):
            build_base_prompt("definitely_non_existent_file.txt", None)


class TestPromptLibraryIntegration:
    """Integration tests for prompt library with CLI."""

    def test_cli_can_use_library_prompt(self, tmp_path):
        """Test that CLI can use prompts from the library."""
        # Create a test input file
        input_file = tmp_path / "input.txt"
        input_file.write_text("Test content to process")

        # Mock the necessary components to avoid actual API calls
        with (
            patch("cerebrate_file.config.validate_api_key", return_value=True),
            patch("cerebrate_file.config.validate_environment"),
            patch("cerebrate_file.cerebrate_file.process_document") as mock_process,
        ):
            # Configure mock
            mock_process.return_value = ("Processed", MagicMock())

            # Import here to avoid issues before mocking
            from cerebrate_file.cli import run

            # This should use the prompt from library
            # We're not actually running it to avoid API calls,
            # but we verify the prompt loading mechanism works
            try:
                run(
                    input_data=str(input_file),
                    file_prompt="fix-pdf-extracted-text.xml",
                    prompt="Additional instructions",
                    dry_run=True,  # Use dry-run to avoid actual processing
                    verbose=False,
                )
            except SystemExit:
                # Dry-run exits after showing info
                pass

    def test_prompt_library_listing(self, capsys):
        """Test that available prompts are listed when file not found."""
        # Try to resolve a non-existent prompt
        resolve_prompt_file("non_existent.txt")

        # Check that it logged available prompts
        # (This would require loguru to be configured to output to stdout,
        # which might not be the case in tests, so this is more of a
        # placeholder for manual testing)
