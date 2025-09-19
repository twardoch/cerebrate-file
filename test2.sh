#!/usr/bin/env bash
cd "$(dirname "$0")"
python -m cerebrate_file --recurse="*.md" --workers=4 --input_data=testdata/in/ --output_data=testdata/out/ --file_prompt=testdata/poml-fix-pdf-extracted-text.xml --explain 
