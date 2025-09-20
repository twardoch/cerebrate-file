#!/usr/bin/env python3
# this_file: test_retry_mechanism.py

"""Test script to verify retry mechanism for API errors."""

import sys
from unittest.mock import Mock, patch

# Test the retry mechanism by simulating 503 errors
def test_503_retry():
    """Test that 503 errors are properly retried."""
    print("Testing 503 Service Unavailable retry mechanism...")

    # Mock the Cerebras SDK to simulate 503 errors
    mock_client = Mock()

    # First call raises 503, second call succeeds
    from cerebrate_file.constants import APIError

    def side_effect(*args, **kwargs):
        if not hasattr(side_effect, 'call_count'):
            side_effect.call_count = 0
        side_effect.call_count += 1

        if side_effect.call_count == 1:
            # First call: simulate 503 error
            mock_error = Mock()
            mock_error.status_code = 503
            mock_error.response = {'message': "We're experiencing high traffic right now! Please try again soon.", 'type': 'too_many_requests_error', 'param': 'queue', 'code': 'queue_exceeded'}
            raise APIError(f"Error code: 503 - {mock_error.response}")
        else:
            # Second call: success
            mock_response = Mock()
            mock_chunk = Mock()
            mock_chunk.choices = [Mock()]
            mock_chunk.choices[0].delta.content = "Test response"
            mock_response.__iter__ = lambda self: iter([mock_chunk])
            mock_response.response = Mock()
            mock_response.response.headers = {}
            return mock_response

    mock_client.chat.completions.create.side_effect = side_effect

    # Test the retry mechanism
    try:
        from cerebrate_file.api_client import make_cerebras_request

        messages = [{"role": "user", "content": "test"}]
        result = make_cerebras_request(
            mock_client,
            messages,
            "llama3.1-8b",
            1000,
            0.7,
            0.9
        )

        print("✓ Retry mechanism worked! Got result:", result[0])
        return True

    except Exception as e:
        print(f"✗ Retry mechanism failed: {e}")
        return False

if __name__ == "__main__":
    success = test_503_retry()
    sys.exit(0 if success else 1)