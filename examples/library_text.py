#!/usr/bin/env python3
# this_file: examples/library_text.py
"""Rewrite text using Cerebras; set CEREBRAS_API_KEY first."""

from cerebrate_file import process_text

result = process_text(
    "The sky are blue.",
    "Correct the grammar. Return only the corrected text.",
)
print(result)
