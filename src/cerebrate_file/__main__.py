#!/usr/bin/env python3
# this_file: src/cerebrate_file/__main__.py

"""Entry point for cerebrate_file package.

This module provides the main entry point for the cerebrate_file package
when run as a module (python -m cerebrate_file) or as a script.
"""

import fire

from .cli import run

__all__ = ["main"]


def main() -> None:
    """Main entry point for cerebrate_file CLI."""
    fire.Fire(run)


if __name__ == "__main__":
    main()
