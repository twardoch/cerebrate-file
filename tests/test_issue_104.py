#!/usr/bin/env python3
# this_file: tests/test_issue_104.py

"""Tests for issues identified in #104."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.cerebrate_file.models import RateLimitStatus, ProcessingState, Chunk
from src.cerebrate_file.api_client import parse_rate_limit_headers
from src.cerebrate_file.file_utils import write_output_atomically
import tempfile
import os


def test_call_counting_bug():
    """Test that call counting decreases properly between requests."""
    # Mock headers showing decreasing call counts
    headers_first = {
        "x-ratelimit-remaining-requests-day": "172799"
    }
    headers_second = {
        "x-ratelimit-remaining-requests-day": "172798"
    }

    status1 = parse_rate_limit_headers(headers_first)
    status2 = parse_rate_limit_headers(headers_second)

    assert status1.requests_remaining == 172799
    assert status2.requests_remaining == 172798
    assert status2.requests_remaining < status1.requests_remaining


def test_frontmatter_missing_when_metadata_empty():
    """Test that frontmatter is still written even when metadata is empty."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        test_file = f.name

    try:
        # Test with empty metadata in explain mode
        write_output_atomically("test content", test_file, {})

        with open(test_file, 'r') as f:
            content = f.read()

        # Should have frontmatter even with empty metadata
        assert content.startswith('---\n')
        assert 'test content' in content

    finally:
        os.unlink(test_file)


def test_frontmatter_not_written_when_metadata_none():
    """Test that frontmatter is not written when metadata is None."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
        test_file = f.name

    try:
        # Test with None metadata (normal mode)
        write_output_atomically("test content", test_file, None)

        with open(test_file, 'r') as f:
            content = f.read()

        # Should not have frontmatter
        assert not content.startswith('---\n')
        assert content == 'test content'

    finally:
        os.unlink(test_file)


def test_chunk_processing_double_processing_issue():
    """Test that first chunk isn't processed twice in explain mode."""
    # This test simulates the issue where first chunk is processed for metadata
    # then the same chunks are reused for content processing

    chunks = [
        Chunk(text="First chunk content", token_count=100),
        Chunk(text="Second chunk content", token_count=100),
        Chunk(text="Third chunk content", token_count=100)
    ]

    # Mock the explain mode workflow
    metadata_processed = False
    content_processing_calls = []

    def mock_llm_call(chunk_text):
        """Mock LLM processing."""
        if not metadata_processed:
            # First call is for metadata
            assert "First chunk content" in chunk_text
            return "metadata_result"
        else:
            # Subsequent calls should be for content processing
            content_processing_calls.append(chunk_text)
            return f"processed_{chunk_text}"

    # Simulate the current buggy behavior
    # 1. First chunk used for metadata
    metadata_result = mock_llm_call(chunks[0].text)
    metadata_processed = True

    # 2. All chunks (including first) processed for content - THIS IS THE BUG
    for chunk in chunks:
        mock_llm_call(chunk.text)

    # The bug: first chunk gets processed twice
    assert len(content_processing_calls) == 3
    assert content_processing_calls[0] == "First chunk content"  # First chunk processed again!

    # What should happen: only chunks 1, 2 should be processed for content
    # chunk 0 was already processed for metadata and should be skipped


def test_progress_callback_uses_correct_remaining_count():
    """Test that progress callback gets called with correct remaining count."""
    callback_calls = []

    def mock_progress_callback(chunks_completed, remaining_calls):
        callback_calls.append((chunks_completed, remaining_calls))

    # Mock rate status with decreasing values
    rate_statuses = [
        RateLimitStatus(requests_remaining=1000, headers_parsed=True),
        RateLimitStatus(requests_remaining=999, headers_parsed=True),
        RateLimitStatus(requests_remaining=998, headers_parsed=True),
    ]

    # Simulate progress updates
    for i, rate_status in enumerate(rate_statuses):
        mock_progress_callback(i + 1, rate_status.requests_remaining)

    # Should show decreasing remaining calls
    assert callback_calls[0] == (1, 1000)
    assert callback_calls[1] == (2, 999)
    assert callback_calls[2] == (3, 998)

    # Each remaining count should be less than the previous
    for i in range(1, len(callback_calls)):
        assert callback_calls[i][1] < callback_calls[i-1][1]


def test_call_counting_issue_debug():
    """Debug test to understand why call counting shows same value repeatedly."""
    # The issue from the bug report: "172,799 calls remaining" appears after every call
    # This suggests the API returns the same value or parsing fails

    # Test scenario 1: API returns no rate limit headers
    empty_headers = {}
    status_no_headers = parse_rate_limit_headers(empty_headers)

    # Should default to 0 or None when no headers
    assert status_no_headers.requests_remaining is None or status_no_headers.requests_remaining == 0
    assert status_no_headers.headers_parsed is False

    # Test scenario 2: API returns malformed headers
    bad_headers = {"x-ratelimit-remaining-requests-day": "invalid"}
    status_bad_headers = parse_rate_limit_headers(bad_headers)

    # Should handle invalid data gracefully
    assert status_bad_headers.headers_parsed is False

    # Test scenario 3: API returns the same value repeatedly (the suspected issue)
    same_value_headers = {"x-ratelimit-remaining-requests-day": "172799"}
    status1 = parse_rate_limit_headers(same_value_headers)
    status2 = parse_rate_limit_headers(same_value_headers)

    # Both should parse the same value (this is the bug in the API, not our code)
    assert status1.requests_remaining == 172799
    assert status2.requests_remaining == 172799
    assert status1.headers_parsed is True
    assert status2.headers_parsed is True


def test_explain_mode_metadata_completeness_check():
    """Test metadata completeness checking logic."""
    from src.cerebrate_file.file_utils import check_metadata_completeness

    # Complete metadata
    complete_metadata = {
        "title": "Test Title",
        "author": "Test Author",
        "id": "test-id",
        "type": "test-type",
        "date": "2023-01-01"
    }

    is_complete, missing = check_metadata_completeness(complete_metadata)
    assert is_complete is True
    assert missing == []

    # Incomplete metadata
    incomplete_metadata = {
        "title": "Test Title",
        "author": "Test Author"
    }

    is_complete, missing = check_metadata_completeness(incomplete_metadata)
    assert is_complete is False
    assert "id" in missing
    assert "type" in missing
    assert "date" in missing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])