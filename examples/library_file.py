#!/usr/bin/env python3
# this_file: examples/library_file.py
"""Transform a UTF-8 file without overwriting its input."""

import sys

from cerebrate_file import process_file

if len(sys.argv) != 3:
    raise SystemExit("Usage: python examples/library_file.py INPUT OUTPUT")

process_file(
    sys.argv[1],
    "Correct grammar. Return only the corrected text.",
    output_path=sys.argv[2],
)
