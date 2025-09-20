#!/usr/bin/env python3
# this_file: tests/test_api_retry.py

"""Tests for API retry functionality."""

import pytest
from unittest.mock import Mock, patch
from cerebrate_file.constants import APIError
from cerebrate_file.api_client import make_cerebras_request


class MockAPIStatusError(Exception):
    """Mock API status error for testing."""

    def __init__(self, status_code, response):
        self.status_code = status_code
        self.response = response
        super().__init__(f"API error {status_code}")


def test_503_error_triggers_retry():
    """Test that 503 errors are converted to retryable APIErrors."""
    mock_client = Mock()

    # Mock the cerebras module to simulate the API error
    with patch("cerebrate_file.api_client.cerebras") as mock_cerebras:
        mock_cerebras.cloud.sdk.APIStatusError = MockAPIStatusError

        # Configure mock to raise 503 error
        mock_client.chat.completions.create.side_effect = MockAPIStatusError(
            503, {'message': "Service unavailable"}
        )

        # Test that the function raises APIError (which is retryable)
        with pytest.raises(APIError) as exc_info:
            make_cerebras_request(
                mock_client,
                [{"role": "user", "content": "test"}],
                "llama3.1-8b",
                1000,
                0.7,
                0.9
            )

        # Verify the error message contains the status code
        assert "503" in str(exc_info.value)


def test_non_retryable_errors_not_converted():
    """Test that 400-level errors are not converted to retryable APIErrors."""
    mock_client = Mock()

    # Mock the cerebras module to simulate the API error
    with patch("cerebrate_file.api_client.cerebras") as mock_cerebras:
        mock_cerebras.cloud.sdk.APIStatusError = MockAPIStatusError

        # Configure mock to raise 400 error (bad request - not retryable)
        error = MockAPIStatusError(400, {'message': "Bad request"})
        mock_client.chat.completions.create.side_effect = error

        # Test that the function raises the original error (not APIError)
        with pytest.raises(MockAPIStatusError) as exc_info:
            make_cerebras_request(
                mock_client,
                [{"role": "user", "content": "test"}],
                "llama3.1-8b",
                1000,
                0.7,
                0.9
            )

        # Verify it's the original error type, not converted to APIError
        assert exc_info.value.status_code == 400


def test_retryable_status_codes():
    """Test that all expected status codes are marked as retryable."""
    retryable_codes = [503, 502, 504, 429]
    mock_client = Mock()

    with patch("cerebrate_file.api_client.cerebras") as mock_cerebras:
        mock_cerebras.cloud.sdk.APIStatusError = MockAPIStatusError

        for status_code in retryable_codes:
            # Configure mock to raise the error
            mock_client.chat.completions.create.side_effect = MockAPIStatusError(
                status_code, {'message': f"Error {status_code}"}
            )

            # Test that the function raises APIError (which is retryable)
            with pytest.raises(APIError) as exc_info:
                make_cerebras_request(
                    mock_client,
                    [{"role": "user", "content": "test"}],
                    "llama3.1-8b",
                    1000,
                    0.7,
                    0.9
                )

            # Verify the error message contains the status code
            assert str(status_code) in str(exc_info.value)


def test_successful_request():
    """Test that successful requests work normally."""
    mock_client = Mock()

    # Mock successful streaming response
    mock_chunk = Mock()
    mock_chunk.choices = [Mock()]
    mock_chunk.choices[0].delta.content = "Test response"

    mock_stream = [mock_chunk]
    mock_stream.response = Mock()
    mock_stream.response.headers = {}

    mock_client.chat.completions.create.return_value = mock_stream

    # Import required modules for the test
    with patch("cerebrate_file.api_client.cerebras"):
        result = make_cerebras_request(
            mock_client,
            [{"role": "user", "content": "test"}],
            "llama3.1-8b",
            1000,
            0.7,
            0.9
        )

    # Verify successful response
    assert result[0] == "Test response"
    assert result[1] is not None  # Rate limit status