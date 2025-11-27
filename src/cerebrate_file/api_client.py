#!/usr/bin/env python3
# this_file: src/cerebrate_file/api_client.py

"""API client utilities for cerebrate_file package.

This module handles all Cerebras API communication including rate limiting,
retries, fallback chain support, and structured output generation.

Supports:
- Primary model (Cerebras by default)
- Fallback chain to OpenAI-compatible APIs on rate limit/quota errors
"""

import json
import time
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

from loguru import logger
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from .constants import (
    METADATA_SCHEMA,
    APIError,
)
from .models import RateLimitStatus
from .settings import ModelConfig, get_settings

try:
    import cerebras.cloud.sdk as cerebras_sdk  # type: ignore[import-not-found]
    from cerebras.cloud.sdk import Cerebras
except ImportError:
    cerebras_sdk = SimpleNamespace(
        APIStatusError=type("APIStatusError", (Exception,), {}),
        RateLimitError=type("RateLimitError", (Exception,), {}),
    )
    Cerebras = None  # type: ignore[assignment]

try:
    import openai as openai_sdk
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[assignment]
    openai_sdk = SimpleNamespace(
        APIStatusError=type("APIStatusError", (Exception,), {}),
        RateLimitError=type("RateLimitError", (Exception,), {}),
    )

cerebras = SimpleNamespace(cloud=SimpleNamespace(sdk=cerebras_sdk))


def _get_sdk_class(name: str) -> type[Exception]:
    """Safely resolve exception classes from the Cerebras SDK for patching/tests."""
    sdk = getattr(getattr(cerebras, "cloud", None), "sdk", cerebras_sdk)
    candidate = getattr(sdk, name, None)
    if isinstance(candidate, type) and issubclass(candidate, BaseException):
        return candidate
    return getattr(cerebras_sdk, name)


def _format_response(response: Any) -> str:
    """Safely format SDK responses for logging without triggering str.format placeholders."""
    if response is None:
        return "None"
    return repr(response).replace("{", "{{").replace("}", "}}").replace("%", "%%")


__all__ = [
    "CerebrasClient",
    "FallbackClient",
    "calculate_backoff_delay",
    "explain_metadata_with_llm",
    "make_cerebras_request",
    "make_request_with_fallback",
    "parse_rate_limit_headers",
]


# Error patterns that trigger fallback
RATE_LIMIT_PATTERNS = [
    "rate limit",
    "rate_limit",
    "too many requests",
    "429",
]
QUOTA_EXCEEDED_PATTERNS = [
    "quota",
    "token_quota_exceeded",
    "tokens per day limit",
    "daily limit",
]


def _is_rate_limit_error(error: Exception) -> bool:
    """Check if an error is a rate limit error."""
    error_str = str(error).lower()
    return any(pattern in error_str for pattern in RATE_LIMIT_PATTERNS)


def _is_quota_exceeded_error(error: Exception) -> bool:
    """Check if an error is a quota exceeded error."""
    error_str = str(error).lower()
    return any(pattern in error_str for pattern in QUOTA_EXCEEDED_PATTERNS)


class CerebrasClient:
    """Manages Cerebras API interactions with rate limiting."""

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Initialize the Cerebras client.

        Args:
            api_key: Cerebras API key
            model: Model name to use (defaults to settings.primary_model.name)
        """
        self.api_key = api_key
        settings = get_settings()
        self.model = model or settings.get_default_model_name()
        self._client = None
        self.rate_status = RateLimitStatus()

    def _get_client(self):
        """Get or create the Cerebras client instance."""
        if self._client is None:
            if Cerebras is None:
                raise APIError(
                    "cerebras-cloud-sdk not available. Install with: uv add cerebras-cloud-sdk"
                )
            self._client = Cerebras(api_key=self.api_key)
        return self._client

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        max_completion_tokens: int,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> tuple[str, RateLimitStatus]:
        """Make a chat completion request.

        Args:
            messages: Chat messages
            max_completion_tokens: Max tokens for completion
            temperature: Sampling temperature (defaults to settings)
            top_p: Nucleus sampling parameter (defaults to settings)

        Returns:
            Tuple of (response text, rate limit status)
        """
        settings = get_settings()
        temp = temperature if temperature is not None else settings.inference.temperature
        tp = top_p if top_p is not None else settings.inference.top_p

        client = self._get_client()
        response_text, self.rate_status = make_cerebras_request(
            client, messages, self.model, max_completion_tokens, temp, tp, False
        )
        return response_text, self.rate_status

    def explain_metadata(
        self,
        existing_metadata: dict[str, Any],
        first_chunk_text: str,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> dict[str, Any]:
        """Generate missing metadata fields using structured output.

        Args:
            existing_metadata: Current metadata
            first_chunk_text: First chunk for context
            temperature: Sampling temperature (defaults to settings)
            top_p: Nucleus sampling parameter (defaults to settings)

        Returns:
            Generated metadata dictionary
        """
        settings = get_settings()
        temp = temperature if temperature is not None else settings.inference.temperature
        tp = top_p if top_p is not None else settings.inference.top_p

        client = self._get_client()
        return explain_metadata_with_llm(
            client,
            existing_metadata,
            first_chunk_text,
            self.model,
            temp,
            tp,
        )

    def calculate_delay(self, next_chunk_tokens: int) -> float:
        """Calculate appropriate delay based on rate limits.

        Args:
            next_chunk_tokens: Estimated tokens for next request

        Returns:
            Delay in seconds
        """
        return calculate_backoff_delay(self.rate_status, next_chunk_tokens)


class FallbackClient:
    """Client for OpenAI-compatible fallback APIs."""

    def __init__(self, model_config: ModelConfig) -> None:
        """Initialize the fallback client.

        Args:
            model_config: Model configuration from settings
        """
        self.config = model_config
        self._client = None

    def _get_client(self):
        """Get or create the OpenAI client instance."""
        if self._client is None:
            if OpenAI is None:
                raise APIError("openai package not available. Install with: uv add openai")
            api_key = self.config.get_api_key()
            if not api_key:
                raise APIError(
                    f"API key not found in environment variable: {self.config.api_key_env}"
                )
            kwargs = {"api_key": api_key}
            if self.config.api_base:
                kwargs["base_url"] = self.config.api_base
            self._client = OpenAI(**kwargs)
        return self._client

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        max_completion_tokens: int,
        temperature: float | None = None,
        top_p: float | None = None,
    ) -> tuple[str, RateLimitStatus]:
        """Make a chat completion request using OpenAI-compatible API.

        Args:
            messages: Chat messages
            max_completion_tokens: Max tokens for completion
            temperature: Sampling temperature (defaults to settings)
            top_p: Nucleus sampling parameter (defaults to settings)

        Returns:
            Tuple of (response text, rate limit status)
        """
        settings = get_settings()
        temp = temperature if temperature is not None else settings.inference.temperature
        tp = top_p if top_p is not None else settings.inference.top_p

        client = self._get_client()

        try:
            # Use streaming for consistency with Cerebras client
            stream = client.chat.completions.create(
                model=self.config.name,
                messages=messages,
                max_tokens=max_completion_tokens,
                temperature=temp,
                top_p=tp,
                stream=True,
            )

            response_text = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    response_text += chunk.choices[0].delta.content

            # Fallback APIs don't provide detailed rate limit headers
            rate_status = RateLimitStatus()
            rate_status.headers_parsed = False

            logger.debug(
                f"Fallback request complete via {self.config.provider}: "
                f"{len(response_text)} chars received"
            )
            return response_text, rate_status

        except Exception as e:
            logger.error(f"Fallback request failed ({self.config.provider}): {e}")
            raise APIError(f"Fallback API error ({self.config.provider}): {e}") from e


def parse_rate_limit_headers(headers: dict[str, str], verbose: bool = False) -> RateLimitStatus:
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
            ratelimit_headers = {
                k: v for k, v in headers.items() if k.lower().startswith("x-ratelimit")
            }
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
            status.requests_remaining = int(headers["x-ratelimit-remaining-requests-day"])
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
                status.requests_reset_time = datetime.now() + timedelta(seconds=seconds_until_reset)
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
) -> float:
    """Calculate optimal delay based on rate limit status.

    Args:
        rate_status: Current rate limit status
        next_chunk_tokens: Estimated tokens for next request

    Returns:
        Delay in seconds
    """
    now = datetime.now()
    settings = get_settings()
    tokens_safety_margin = settings.rate_limiting.tokens_safety_margin
    requests_safety_margin = settings.rate_limiting.requests_safety_margin

    # Only apply rate limiting if we successfully parsed headers
    if not rate_status.headers_parsed:
        logger.debug("No rate limit headers parsed, using minimal delay")
        return 0.1

    # Rate-based safety thresholds
    tokens_per_minute_limit = rate_status.tokens_limit if rate_status.tokens_limit > 0 else 400000
    tokens_per_second_limit = tokens_per_minute_limit / 60.0

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
    safety_threshold = next_chunk_tokens + tokens_safety_margin
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
            (now - rate_status.last_updated).total_seconds() if rate_status.last_updated else 0
        )
        if time_since_update < 1.0:  # Recent update, check consumption rate
            # Conservative pacing: don't exceed 80% of max rate
            safe_tokens_per_second = tokens_per_second_limit * 0.8

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
        and rate_status.requests_remaining < requests_safety_margin
    ):
        delay = 2.0
        logger.info(
            f"Low request quota ({rate_status.requests_remaining} < {requests_safety_margin}), "
            f"conservative delay: {delay}s"
        )
        return delay

    # All checks passed - minimal delay for optimal throughput
    return 0.1


@retry(
    stop=stop_after_attempt(8),
    wait=wait_fixed(0),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, APIError)),
    before_sleep=before_sleep_log(logger, "INFO"),
    reraise=True,
)
def explain_metadata_with_llm(
    client,
    existing_metadata: dict[str, Any],
    first_chunk_text: str,
    model: str,
    temp: float,
    top_p: float,
) -> dict[str, Any]:
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
        import cerebras.cloud.sdk

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

        logger.info(f"Metadata explanation successful: {len(generated_metadata)} fields generated")
        return generated_metadata

    except Exception as e:
        rate_limit_error = _get_sdk_class("RateLimitError")
        api_status_error = _get_sdk_class("APIStatusError")

        if isinstance(e, rate_limit_error):
            logger.warning(f"Rate limit hit during metadata explanation: {e}")
            raise APIError(f"Rate limit error: {e}") from e

        if isinstance(e, api_status_error):
            logger.error(f"API error during metadata explanation {e.status_code}: {e.response}")
            if getattr(e, "status_code", None) in (503, 502, 504, 429):
                logger.warning(
                    f"Retryable metadata explanation error {e.status_code}, will retry with backoff"
                )
                raise APIError(
                    f"Error code: {e.status_code} - {_format_response(getattr(e, 'response', None))}"
                ) from e
            raise e

        logger.error(f"Metadata explanation failed: {e}")
        return {}


def _make_cerebras_request_impl(
    client,
    messages: list[dict[str, str]],
    model: str,
    max_completion_tokens: int,
    temperature: float,
    top_p: float,
    verbose: bool = False,
) -> tuple[str, RateLimitStatus]:
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
                logger.debug("Rate limit headers parsed from stream response")

            # If we have a last chunk with response headers, try to get updated headers
            if (
                last_chunk
                and hasattr(last_chunk, "_raw_response")
                and hasattr(last_chunk._raw_response, "headers")
            ):
                final_headers_dict = dict(last_chunk._raw_response.headers)
                updated_rate_status = parse_rate_limit_headers(final_headers_dict, verbose=verbose)
                # Use updated headers if they were successfully parsed
                if updated_rate_status.headers_parsed:
                    rate_status = updated_rate_status
                    logger.debug("Rate limit headers updated from final chunk")

        except Exception as e:
            logger.debug(f"Could not parse rate limit headers: {e}")

        logger.debug(f"Streaming complete: {len(response_text)} chars received")
        return response_text, rate_status

    except Exception as e:
        rate_limit_error = _get_sdk_class("RateLimitError")
        api_status_error = _get_sdk_class("APIStatusError")

        if isinstance(e, rate_limit_error):
            logger.warning(f"Rate limit hit: {e}")
            raise APIError(f"Rate limit error: {e}") from e

        if isinstance(e, api_status_error):
            formatted_response = _format_response(getattr(e, "response", None))
            logger.error(f"API error {getattr(e, 'status_code', 'unknown')}: {formatted_response}")
            if getattr(e, "status_code", None) in (503, 502, 504, 429):
                logger.warning(f"Retryable error {e.status_code}, will retry with backoff")
                raise APIError(f"Error code: {e.status_code} - {formatted_response}") from e
            raise e

        logger.error(f"Unexpected error in Cerebras request: {e}")
        raise e


def make_cerebras_request(
    client,
    messages: list[dict[str, str]],
    model: str,
    max_completion_tokens: int,
    temperature: float,
    top_p: float,
    verbose: bool = False,
) -> tuple[str, RateLimitStatus]:
    """Make streaming Cerebras request (single attempt, no retry)."""
    return _make_cerebras_request_impl(
        client,
        messages,
        model,
        max_completion_tokens,
        temperature,
        top_p,
        verbose,
    )


def make_request_with_fallback(
    primary_client,
    messages: list[dict[str, str]],
    model: str,
    max_completion_tokens: int,
    temperature: float,
    top_p: float,
    verbose: bool = False,
) -> tuple[str, RateLimitStatus, str]:
    """Make a request with retry and automatic fallback on rate limit or quota errors.

    Attempts the primary model first with configured retries, then falls back to
    configured fallback models if rate limits or quota errors are encountered.

    Args:
        primary_client: Primary Cerebras client instance
        messages: Chat messages for the request
        model: Primary model name
        max_completion_tokens: Maximum tokens for completion
        temperature: Model temperature
        top_p: Model top_p
        verbose: Enable verbose logging

    Returns:
        Tuple of (response_text, rate_limit_status, model_used)
        model_used indicates which model actually produced the response
    """
    settings = get_settings()
    max_retries = settings.rate_limiting.max_retry_attempts
    last_error: Exception | None = None

    # Try primary model with retries
    should_try_fallback = False
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.info(f"Retry {attempt}/{max_retries} for primary model: {model}")
            else:
                logger.debug(f"Attempting request with primary model: {model}")

            response_text, rate_status = make_cerebras_request(
                primary_client,
                messages,
                model,
                max_completion_tokens,
                temperature,
                top_p,
                verbose,
            )
            return response_text, rate_status, model

        except Exception as e:
            last_error = e
            error_str = str(e)

            # Check if this is a retryable/fallback-worthy error
            is_rate_limit = _is_rate_limit_error(e)
            is_quota_exceeded = _is_quota_exceeded_error(e)

            if is_rate_limit or is_quota_exceeded:
                if attempt < max_retries:
                    # Retry with backoff
                    backoff = 2**attempt  # 1, 2, 4 seconds
                    logger.warning(
                        f"Retryable error (attempt {attempt + 1}/{max_retries + 1}): {error_str}. "
                        f"Retrying in {backoff}s..."
                    )
                    time.sleep(backoff)
                    continue
                else:
                    # All retries exhausted, check if we should fallback
                    if is_rate_limit and settings.rate_limiting.fallback_on_rate_limit:
                        logger.warning(
                            f"Rate limit error after {max_retries + 1} attempts, "
                            f"attempting fallback: {error_str}"
                        )
                        should_try_fallback = True
                    elif is_quota_exceeded and settings.rate_limiting.fallback_on_quota_exceeded:
                        logger.warning(
                            f"Quota exceeded after {max_retries + 1} attempts, "
                            f"attempting fallback: {error_str}"
                        )
                        should_try_fallback = True
                    else:
                        raise
                    break
            else:
                # Non-retryable error, raise immediately
                raise

    if not should_try_fallback:
        if last_error:
            raise last_error
        raise APIError("Primary model failed")

    # Try fallback models
    available_fallbacks = settings.get_available_fallbacks()

    if not available_fallbacks:
        logger.error("No fallback models available, re-raising original error")
        if last_error:
            raise last_error
        raise APIError("No fallback models configured")

    for i, fallback_config in enumerate(available_fallbacks):
        try:
            logger.info(
                f"Trying fallback model {i + 1}/{len(available_fallbacks)}: "
                f"{fallback_config.name} ({fallback_config.provider})"
            )

            fallback_client = FallbackClient(fallback_config)

            # Adjust max_completion_tokens if fallback model has lower limit
            adjusted_max_tokens = min(max_completion_tokens, fallback_config.max_output_tokens)

            response_text, rate_status = fallback_client.chat_completion(
                messages,
                adjusted_max_tokens,
                temperature,
                top_p,
            )

            logger.info(
                f"Fallback successful using {fallback_config.name} ({fallback_config.provider})"
            )
            return response_text, rate_status, fallback_config.name

        except Exception as fallback_error:
            logger.warning(f"Fallback {fallback_config.name} failed: {fallback_error}")
            last_error = fallback_error
            continue

    # All fallbacks failed
    logger.error("All fallback models failed")
    if last_error:
        raise APIError(f"All models failed. Last error: {last_error}") from last_error
    raise APIError("All models failed")
