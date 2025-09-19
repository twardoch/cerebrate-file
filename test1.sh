#!/usr/bin/env bash
cd "$(dirname "$0")"
python -m cerebrate_file --workers=4 --input_data=testdata/ex/01.md --output_data=testdata/ex/02.md --explain --file_prompt=testdata/poml-fix-pdf-extracted-text.xml --verbose