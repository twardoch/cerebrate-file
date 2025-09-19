#!/bin/bash
# this_file: testdata/test.sh

# Test script for cereproc.py
# Tests basic functionality with different chunking modes

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CEREPROC="$PROJECT_DIR/cereproc.py"

echo "=== cereproc.py Test Suite ==="
echo "Project dir: $PROJECT_DIR"
echo "Test data: $SCRIPT_DIR"
echo

# Check if cereproc.py exists
if [[ ! -f "$CEREPROC" ]]; then
    echo "ERROR: cereproc.py not found at $CEREPROC"
    exit 1
fi

# Check if test data exists
if [[ ! -f "$SCRIPT_DIR/test1.md" ]]; then
    echo "ERROR: test1.md not found"
    exit 1
fi

# Check for API key
if [[ -z "$CEREBRAS_API_KEY" ]]; then
    echo "WARNING: CEREBRAS_API_KEY not set - tests will fail at API call"
    echo "Set it with: export CEREBRAS_API_KEY='csk-...'"
    echo
fi

# Test 1: Basic text mode chunking (dry run with early exit)
echo "Test 1: Basic text mode processing..."
python "$CEREPROC" \
    --input_data "$SCRIPT_DIR/test1.md" \
    --output_data "$SCRIPT_DIR/test_output_text.txt" \
    --file_prompt "$SCRIPT_DIR/test_prompt.txt" \
    --data_format text \
    --chunk_size 1000 \
    --example_size 100 \
    --verbose

if [[ -f "$SCRIPT_DIR/test_output_text.txt" ]]; then
    echo "✓ Text mode output created: $(wc -c < "$SCRIPT_DIR/test_output_text.txt") bytes"
else
    echo "✗ Text mode output not created"
    exit 1
fi

# Test 2: Markdown mode chunking
echo
echo "Test 2: Markdown mode processing..."
python "$CEREPROC" \
    --input_data "$SCRIPT_DIR/test1.md" \
    --output_data "$SCRIPT_DIR/test_output_markdown.txt" \
    --data_format markdown \
    --chunk_size 1500 \
    --max_tokens_ratio 50 \
    --verbose

if [[ -f "$SCRIPT_DIR/test_output_markdown.txt" ]]; then
    echo "✓ Markdown mode output created: $(wc -c < "$SCRIPT_DIR/test_output_markdown.txt") bytes"
else
    echo "✗ Markdown mode output not created"
    exit 1
fi

# Test 3: Semantic mode (if available)
echo
echo "Test 3: Semantic mode processing..."
python "$CEREPROC" \
    --input_data "$SCRIPT_DIR/test1.md" \
    --output_data "$SCRIPT_DIR/test_output_semantic.txt" \
    --data_format semantic \
    --chunk_size 2000 \
    --example_size 0 \
    --verbose

if [[ -f "$SCRIPT_DIR/test_output_semantic.txt" ]]; then
    echo "✓ Semantic mode output created: $(wc -c < "$SCRIPT_DIR/test_output_semantic.txt") bytes"
else
    echo "✗ Semantic mode output not created"
    exit 1
fi

# Test 4: Small chunk size to test continuity
echo
echo "Test 4: Small chunks with continuity..."
python "$CEREPROC" \
    --input_data "$SCRIPT_DIR/test1.md" \
    --output_data "$SCRIPT_DIR/test_output_small.txt" \
    --chunk_size 500 \
    --example_size 50 \
    --max_tokens_ratio 25 \
    --verbose

if [[ -f "$SCRIPT_DIR/test_output_small.txt" ]]; then
    echo "✓ Small chunk output created: $(wc -c < "$SCRIPT_DIR/test_output_small.txt") bytes"
else
    echo "✗ Small chunk output not created"
    exit 1
fi

# Summary
echo
echo "=== Test Summary ==="
echo "All tests completed successfully!"
echo
echo "Output files created:"
ls -la "$SCRIPT_DIR"/test_output_*.txt
echo
echo "To clean up test outputs:"
echo "rm $SCRIPT_DIR/test_output_*.txt"

echo
echo "Manual verification steps:"
echo "1. Check that chunk counts are reasonable for file size"
echo "2. Verify continuity blocks appear in multi-chunk outputs"
echo "3. Confirm token limits are respected in verbose logs"
echo "4. Review rate limiting behavior in logs"
echo "5. Test with different chunk sizes and formats"