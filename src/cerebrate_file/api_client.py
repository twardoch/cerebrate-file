#!/usr/bin/env python3
# this_file: src/cerebrate_file/api_client.py

"""API client utilities for cerebrate_file package.

This module handles all Cerebras API communication including rate limiting,
retries, and structured output generation.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .constants import (
    APIError,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    METADATA_SCHEMA,
    REQUESTS_SAFETY_MARGIN,
    TOKENS_SAFETY_MARGIN,
)
from .error_recovery import format_error_with_suggestions, with_retry, RetryConfig
from .models import RateLimitStatus

__all__ = [
    "CerebrasClient",
    "parse_rate_limit_headers",
    "calculate_backoff_delay",
    "explain_metadata_with_llm",
    "make_cerebras_request",
]


class CerebrasClient:
    """Manages Cerebras API interactions with rate limiting."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        """Initialize the Cerebras client.

        Args:
            api_key: Cerebras API key
            model: Model name to use
        """
        self.api_key = api_key
        self.model = model
        self._client = None
        self.rate_status = RateLimitStatus()

    def _get_client(self):
        """Get or create the Cerebras client instance."""
        if self._client is None:
            try:
                import cerebras.cloud.sdk as cerebras
                from cerebras.cloud.sdk import Cerebras

                self._client = Cerebras(api_key=self.api_key)
            except ImportError:
                raise APIError(
                    "cerebras-cloud-sdk not available. Install with: uv add cerebras-cloud-sdk"
                )
        return self._client

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_completion_tokens: int,
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
        stream: bool = True,
    ) -> Tuple[str, RateLimitStatus]:
        """Make a chat completion request.

        Args:
            messages: Chat messages
            max_completion_tokens: Max tokens for completion
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            stream: Whether to stream response

        Returns:
            Tuple of (response text, rate limit status)
        """
        client = self._get_client()
        response_text, self.rate_status = make_cerebras_request(
            client, messages, self.model, max_completion_tokens, temperature, top_p, False
        )
        return response_text, self.rate_status

    def explain_metadata(
        self,
        existing_metadata: Dict[str, Any],
        first_chunk_text: str,
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
    ) -> Dict[str, Any]:
        """Generate missing metadata fields using structured output.

        Args:
            existing_metadata: Current metadata
            first_chunk_text: First chunk for context
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter

        Returns:
            Generated metadata dictionary
        """
        client = self._get_client()
        return explain_metadata_with_llm(
            client,
            existing_metadata,
            first_chunk_text,
            self.model,
            temperature,
            top_p,
        )

    def calculate_delay(self, next_chunk_tokens: int) -> float:
        """Calculate appropriate delay based on rate limits.

        Args:
            next_chunk_tokens: Estimated tokens for next request

        Returns:
            Delay in seconds
        """
        return calculate_backoff_delay(self.rate_status, next_chunk_tokens)


def parse_rate_limit_headers(headers: Dict[str, str], verbose: bool = False) -> RateLimitStatus:
    """Extract rate limit info from response headers.

    Args:
        headers: HTTP response headers
        verbose: If True, log all x-ratelimit-* headers

    Returns:
        RateLimitStatus object
    """
    try:
        status = RateLimitStatus()
        found_any_headers = False

        # In verbose mode, log all x-ratelimit-* headers
        if verbose:
            ratelimit_headers = {k: v for k, v in headers.items() if k.lower().startswith('x-ratelimit')}
            if ratelimit_headers:
                logger.info(f"All x-ratelimit headers: {ratelimit_headers}")
            else:
                logger.info("No x-ratelimit headers found in response")

        # Parse limits (maximum allowed)
        if "x-ratelimit-limit-requests-day" in headers:
            status.requests_limit = int(headers["x-ratelimit-limit-requests-day"])
            found_any_headers = True

        if "x-ratelimit-limit-tokens-minute" in headers:
            status.tokens_limit = int(headers["x-ratelimit-limit-tokens-minute"])
            found_any_headers = True

        # Parse remaining requests (daily limit)
        if "x-ratelimit-remaining-requests-day" in headers:
            status.requests_remaining = int(
                headers["x-ratelimit-remaining-requests-day"]
            )
            found_any_headers = True

        # Parse remaining tokens (per-minute limit)
        if "x-ratelimit-remaining-tokens-minute" in headers:
            status.tokens_remaining = int(headers["x-ratelimit-remaining-tokens-minute"])
            found_any_headers = True

        # Parse reset time for tokens (per-minute)
        if "x-ratelimit-reset-tokens-minute" in headers:
            reset_value = headers["x-ratelimit-reset-tokens-minute"]
            try:
                # Reset time is in seconds from now
                seconds_until_reset = float(reset_value)
                status.reset_time = datetime.now() + timedelta(seconds=seconds_until_reset)
                found_any_headers = True
            except ValueError:
                logger.debug(f"Could not parse reset time: {reset_value}")

        # Parse reset time for requests (daily)
        if "x-ratelimit-reset-requests-day" in headers:
            reset_value = headers["x-ratelimit-reset-requests-day"]
            try:
                seconds_until_reset = float(reset_value)
                status.requests_reset_time = datetime.now() + timedelta(
                    seconds=seconds_until_reset
                )
                found_any_headers = True
            except ValueError:
                logger.debug(f"Could not parse request reset time: {reset_value}")

        # Mark that we successfully parsed headers and update timestamp
        status.headers_parsed = found_any_headers
        status.last_updated = datetime.now()

        logger.debug(
            f"Rate limit status: {status.requests_remaining}/{status.requests_limit} requests, "
            f"{status.tokens_remaining}/{status.tokens_limit} tokens remaining, "
            f"parsed: {status.headers_parsed}"
        )

        return status

    except Exception as e:
        logger.warning(f"Failed to parse rate limit headers: {e}")
        return RateLimitStatus()


def calculate_backoff_delay(
    rate_status: RateLimitStatus,
    next_chunk_tokens: int,
    processing_state: Optional[object] = None,
) -> float:
    """Calculate optimal delay based on rate limit status.

    Args:
        rate_status: Current rate limit status
        next_chunk_tokens: Estimated tokens for next request
        processing_state: Optional processing state for rate tracking

    Returns:
        Delay in seconds
    """
    now = datetime.now()

    # Only apply rate limiting if we successfully parsed headers
    if not rate_status.headers_parsed:
        logger.debug("No rate limit headers parsed, using minimal delay")
        return 0.1

    # Rate-based safety thresholds
    TOKENS_PER_MINUTE_LIMIT = (
        rate_status.tokens_limit if rate_status.tokens_limit > 0 else 400000
    )
    TOKENS_PER_SECOND_LIMIT = TOKENS_PER_MINUTE_LIMIT / 60.0

    # Critical shortage - immediate wait until reset
    if rate_status.tokens_remaining < next_chunk_tokens:
        if rate_status.reset_time and rate_status.reset_time > now:
            delay = (rate_status.reset_time - now).total_seconds()
            logger.info(
                f"Critical token shortage ({rate_status.tokens_remaining} < {next_chunk_tokens}), "
                f"waiting {delay:.1f}s until reset"
            )
            return min(delay, 60.0)  # Cap at 60 seconds max

    # Safety margin check - entering dangerous territory
    safety_threshold = next_chunk_tokens + TOKENS_SAFETY_MARGIN
    if rate_status.tokens_remaining < safety_threshold:
        # Calculate time until we have safe tokens again
        if rate_status.reset_time and rate_status.reset_time > now:
            delay = (rate_status.reset_time - now).total_seconds() * 0.1
            logger.info(
                f"Approaching token safety margin ({rate_status.tokens_remaining} < {safety_threshold}), "
                f"conservative delay: {delay:.1f}s"
            )
            return min(max(delay, 1.0), 10.0)  # Between 1-10 seconds

    # Rate-based pacing - don't consume faster than sustainable rate
    if rate_status.tokens_limit > 0:
        time_since_update = (
            (now - rate_status.last_updated).total_seconds()
            if rate_status.last_updated
            else 0
        )
        if time_since_update < 1.0:  # Recent update, check consumption rate
            # Conservative pacing: don't exceed 80% of max rate
            safe_tokens_per_second = TOKENS_PER_SECOND_LIMIT * 0.8

            # If next request would exceed safe rate, add small delay
            if next_chunk_tokens > safe_tokens_per_second:
                delay = (next_chunk_tokens / safe_tokens_per_second) - 1.0
                if delay > 0:
                    logger.debug(
                        f"Rate pacing: {next_chunk_tokens} tokens > {safe_tokens_per_second:.0f} safe rate, "
                        f"delay: {delay:.2f}s"
                    )
                    return min(delay, 2.0)  # Cap at 2 seconds for rate pacing

    # Request quota safety check
    if (
        rate_status.requests_remaining >= 0
        and rate_status.requests_remaining < REQUESTS_SAFETY_MARGIN
    ):
        delay = 2.0
        logger.info(
            f"Low request quota ({rate_status.requests_remaining} < {REQUESTS_SAFETY_MARGIN}), "
            f"conservative delay: {delay}s"
        )
        return delay

    # All checks passed - minimal delay for optimal throughput
    return 0.1


def explain_metadata_with_llm(
    client,
    existing_metadata: Dict[str, Any],
    first_chunk_text: str,
    model: str,
    temp: float,
    top_p: float,
) -> Dict[str, Any]:
    """Use structured outputs to generate missing metadata fields.

    Args:
        client: Cerebras client instance
        existing_metadata: Current metadata dictionary
        first_chunk_text: First chunk of content for context
        model: Model name to use
        temp: Model temperature
        top_p: Model top_p

    Returns:
        Dictionary with generated metadata fields
    """
    try:
        # Create explanation prompt
        existing_json = json.dumps(existing_metadata, separators=(",", ":"))

        # Truncate first chunk if too long for explanation
        max_chunk_chars = 4000  # Conservative limit for explanation context
        truncated_chunk = (
            first_chunk_text[:max_chunk_chars] + "..."
            if len(first_chunk_text) > max_chunk_chars
            else first_chunk_text
        )

        explanation_prompt = f"""<TASK>
Look at the JSON metadata and the first chunk of text below. Based on the text content, fill out any missing fields in the metadata. Return only the JSON with the missing fields filled in.

Existing metadata: {existing_json}
First chunk: {truncated_chunk}
</TASK>"""

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that analyzes documents and fills in missing metadata fields.",
            },
            {"role": "user", "content": explanation_prompt},
        ]

        logger.debug(
            f"Making metadata explanation request with {len(truncated_chunk)} chars context"
        )

        # Make structured output request
        response = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temp,
            top_p=top_p,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "metadata_schema",
                    "strict": True,
                    "schema": METADATA_SCHEMA,
                },
            },
        )

        # Parse the structured response
        response_content = response.choices[0].message.content
        generated_metadata = json.loads(response_content)

        logger.info(
            f"Metadata explanation successful: {len(generated_metadata)} fields generated"
        )
        return generated_metadata

    except Exception as e:
        logger.error(f"Metadata explanation failed: {e}")
        return {}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
)
def make_cerebras_request(
    client,
    messages: List[Dict[str, str]],
    model: str,
    max_completion_tokens: int,
    temperature: float,
    top_p: float,
    verbose: bool = False,
) -> Tuple[str, RateLimitStatus]:
    """Make streaming request to Cerebras API with retry logic.

    Args:
        client: Cerebras client instance
        messages: Chat messages for the request
        model: Model name
        max_completion_tokens: Maximum tokens for completion
        temperature: Model temperature
        top_p: Model top_p
        verbose: Enable verbose logging of rate limit headers

    Returns:
        Tuple of (response_text, rate_limit_status)
    """
    try:
        import cerebras.cloud.sdk

        stream = client.chat.completions.create(
            messages=messages,
            model=model,
            stream=True,
            max_completion_tokens=max_completion_tokens,
            temperature=temperature,
            top_p=top_p,
        )

        response_text = ""
        rate_status = RateLimitStatus()
        last_chunk = None

        for chunk in stream:
            if chunk.choices[0].delta.content:
                response_text += chunk.choices[0].delta.content
            last_chunk = chunk

        # Extract rate limit info from the final chunk/stream response headers
        try:
            # Try to get headers from stream response (initial headers)
            if hasattr(stream, "response") and hasattr(stream.response, "headers"):
                headers_dict = dict(stream.response.headers)
                rate_status = parse_rate_limit_headers(headers_dict, verbose=verbose)
                logger.debug(f"Rate limit headers parsed from stream response")

            # If we have a last chunk with response headers, try to get updated headers
            if last_chunk and hasattr(last_chunk, "_raw_response") and hasattr(last_chunk._raw_response, "headers"):
                final_headers_dict = dict(last_chunk._raw_response.headers)
                updated_rate_status = parse_rate_limit_headers(final_headers_dict, verbose=verbose)
                # Use updated headers if they were successfully parsed
                if updated_rate_status.headers_parsed:
                    rate_status = updated_rate_status
                    logger.debug(f"Rate limit headers updated from final chunk")

        except Exception as e:
            logger.debug(f"Could not parse rate limit headers: {e}")

        logger.debug(f"Streaming complete: {len(response_text)} chars received")
        return response_text, rate_status

    except cerebras.cloud.sdk.RateLimitError as e:
        logger.warning(f"Rate limit hit: {e}")
        # For rate limits, we want to retry after a delay
        raise e
    except cerebras.cloud.sdk.APIStatusError as e:
        logger.error(f"API error {e.status_code}: {e.response}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in Cerebras request: {e}")
        raise e