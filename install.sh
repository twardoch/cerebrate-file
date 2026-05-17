#!/usr/bin/env bash
# install.sh — Install cerebrate-file locally
# cerebrate-file processes files using Cerebras AI (LLM inference) with semantic chunking
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Installing cerebrate-file..."
uv pip install -e . 2>/dev/null || pip install -e . 2>/dev/null || echo "Install failed"
echo "Done."
