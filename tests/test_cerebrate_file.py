#!/usr/bin/env python3
# this_file: tests/test_cerebrate_file.py

"""Tests for core helpers in cerebrate_file.cerebrate_file."""

import math

from cerebrate_file.cerebrate_file import calculate_completion_budget
from cerebrate_file.constants import (
    MAX_OUTPUT_TOKENS,
    MIN_COMPLETION_TOKENS,
    REASONING_COMPLETION_RATIO,
)


def test_calculate_completion_budget_enforces_minimum_floor() -> None:
    """Even tiny chunks should reserve a large completion budget."""

    budget = calculate_completion_budget(chunk_tokens=10, max_tokens_ratio=100)
    assert budget == MIN_COMPLETION_TOKENS, "Should allocate the minimum completion floor"


def test_calculate_completion_budget_applies_reasoning_multiplier() -> None:
    """Chunks need extra headroom for Cerebras reasoning tokens."""

    expected = math.ceil(1000 * REASONING_COMPLETION_RATIO / 100)
    budget = calculate_completion_budget(chunk_tokens=1000, max_tokens_ratio=80)
    assert (
        budget == expected
    ), "Reasoning multiplier should dominate when user ratio is lower than required"


def test_calculate_completion_budget_caps_at_max_output() -> None:
    """Budgets should still respect the 40K token hard cap."""

    budget = calculate_completion_budget(chunk_tokens=100000, max_tokens_ratio=100)
    assert budget == MAX_OUTPUT_TOKENS, "Budget must not exceed model limits"
