#!/usr/bin/env python3
# this_file: tests/test_brace_patterns.py

"""Tests for brace pattern expansion in recursive processing."""

import pytest

from cerebrate_file.recursive import expand_brace_patterns


class TestBracePatternExpansion:
    """Ensure brace pattern expansion functionality."""

    def test_simple_brace_pattern(self):
        """Ensure basic brace pattern expansion."""
        result = expand_brace_patterns("*.{md,py}")
        expected = ["*.md", "*.py"]
        assert result == expected

    def test_complex_brace_pattern(self):
        """Ensure complex recursive brace pattern."""
        result = expand_brace_patterns("**/*.{txt,md,py,js}")
        expected = ["**/*.txt", "**/*.md", "**/*.py", "**/*.js"]
        assert result == expected

    def test_single_extension(self):
        """Ensure pattern with single extension in braces."""
        result = expand_brace_patterns("*.{md}")
        expected = ["*.md"]
        assert result == expected

    def test_no_braces(self):
        """Ensure pattern without braces returns as-is."""
        result = expand_brace_patterns("**/*.md")
        expected = ["**/*.md"]
        assert result == expected

    def test_empty_options(self):
        """Ensure handling of empty options in braces."""
        result = expand_brace_patterns("*.{md,,py}")
        expected = ["*.md", "*.py"]  # Empty option should be filtered out
        assert result == expected

    def test_whitespace_in_options(self):
        """Ensure handling of whitespace in brace options."""
        result = expand_brace_patterns("*.{ md , py , js }")
        expected = ["*.md", "*.py", "*.js"]
        assert result == expected

    def test_nested_directories(self):
        """Ensure brace patterns with nested directory structures."""
        result = expand_brace_patterns("src/**/*.{py,js}")
        expected = ["src/**/*.py", "src/**/*.js"]
        assert result == expected

    def test_multiple_directory_levels(self):
        """Ensure complex directory patterns with braces."""
        result = expand_brace_patterns("**/tests/**/*.{py,js,md}")
        expected = ["**/tests/**/*.py", "**/tests/**/*.js", "**/tests/**/*.md"]
        assert result == expected

    def test_mixed_patterns(self):
        """Ensure patterns that mix regular and brace patterns."""
        result = expand_brace_patterns("docs/*.{md,txt}")
        expected = ["docs/*.md", "docs/*.txt"]
        assert result == expected

    def test_malformed_braces(self):
        """Ensure handling of malformed brace patterns."""
        # Missing closing brace
        result = expand_brace_patterns("*.{md,py")
        expected = ["*.{md,py"]  # Should return as-is
        assert result == expected

        # Missing opening brace
        result = expand_brace_patterns("*.md,py}")
        expected = ["*.md,py}"]  # Should return as-is
        assert result == expected

    def test_empty_braces(self):
        """Ensure handling of empty braces."""
        result = expand_brace_patterns("*.{}")
        expected = ["*.{}"]  # Should return as-is
        assert result == expected

    def test_numeric_extensions(self):
        """Ensure brace patterns with numeric extensions."""
        result = expand_brace_patterns("backup.{1,2,3}")
        expected = ["backup.1", "backup.2", "backup.3"]
        assert result == expected
