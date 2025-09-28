---
layout: default
title: Examples
nav_order: 6
has_children: true
---

# Examples
{: .no_toc }

Practical use cases for Cerebrate File

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Documentation Processing

### README Enhancement

```bash
# Add structure and clarity
cerebrate-file README.md \
  --prompt "Add relevant emojis to headers, improve clarity, and ensure all sections are complete" \
  --output README_enhanced.md

# Generate from notes
cerebrate-file project_notes.txt \
  --prompt "Convert to well-structured README with sections: Overview, Installation, Usage, API, Contributing" \
  --output README.md
```

### API Documentation Generation

```bash
# From Python code
cerebrate-file api.py \
  --data_format code \
  --prompt "Extract all functions and classes, generate markdown API documentation with examples" \
  --output api_docs.md

# From multiple files
cerebrate-file ./src \
  --recurse "**/*.py" \
  --prompt "Generate comprehensive API documentation in markdown format" \
  --output ./docs/api/
```

### Changelog Generation

```bash
# From git log
git log --oneline -n 50 > commits.txt
cerebrate-file commits.txt \
  --prompt "Generate a CHANGELOG.md with sections: Added, Changed, Fixed, Removed" \
  --output CHANGELOG.md

# Update existing
cerebrate-file CHANGELOG.md \
  --file_prompt new_features.txt \
  --prompt "Add these features to the Unreleased section"
```

## Code Transformation

### Adding Type Hints

```bash
# Single file
cerebrate-file utils.py \
  --data_format code \
  --prompt "Add comprehensive type hints to all functions and methods" \
  --chunk_size 24000

# Entire codebase
cerebrate-file ./src \
  --recurse "**/*.py" \
  --prompt "Add type hints following PEP 484, use Union types where appropriate" \
  --output ./typed_src/
```

### Code Refactoring

```bash
# Modernize syntax
cerebrate-file legacy.py \
  --data_format code \
  --prompt "Refactor to use modern Python features: f-strings, pathlib, dataclasses, type hints" \
  --output modern.py

# Apply patterns
cerebrate-file service.py \
  --prompt "Refactor using dependency injection and repository pattern" \
  --temp 0.4  # Lower temp for consistency
```

### Test Generation

```bash
# Generate tests
cerebrate-file calculator.py \
  --data_format code \
  --prompt "Generate comprehensive pytest test cases with edge cases and fixtures" \
  --output test_calculator.py

# Extend existing tests
cerebrate-file test_utils.py \
  --prompt "Add edge case tests for error conditions and boundary values"
```

## Content Transformation

### Translation

```bash
# Single document
cerebrate-file article.md \
  --prompt "Translate to Spanish, preserve all markdown formatting and code blocks" \
  --output articulo.md

# Batch process
cerebrate-file ./content/en \
  --recurse "**/*.md" \
  --prompt "Translate to French, maintain technical terms in English with translations in parentheses" \
  --output ./content/fr/
```

### Summarization

```bash
# Executive summary
cerebrate-file report.pdf.txt \
  --prompt "Create executive summary: 500 words max, bullet points for key findings, action items section" \
  --output summary.md

# Chapter summaries
cerebrate-file book.md \
  --data_format semantic \
  --chunk_size 48000 \
  --prompt "Summarize each chapter in 200 words, maintain narrative flow" \
  --output chapter_summaries.md
```

### Style Transformation

```bash
# Technical to plain English
cerebrate-file technical_manual.md \
  --prompt "Rewrite for general audience, explain technical terms, use analogies" \
  --output user_guide.md

# Formal to conversational
cerebrate-file formal_report.md \
  --prompt "Rewrite in conversational tone, add examples, use 'you' and 'we'" \
  --temp 0.8  # Higher temp for variety
```

## Data Processing

### CSV/JSON Processing

```bash
# CSV to markdown
cerebrate-file data.csv \
  --data_format text \
  --prompt "Convert to markdown table with proper formatting, add summary statistics" \
  --output data_table.md

# JSON to docs
cerebrate-file api_spec.json \
  --prompt "Generate human-readable API documentation with examples for each endpoint" \
  --output api_guide.md
```

### Log Analysis

```bash
# Error patterns
cerebrate-file app.log \
  --data_format text \
  --chunk_size 32000 \
  --prompt "Identify error patterns, group by type, suggest fixes" \
  --output error_report.md

# Performance issues
cerebrate-file performance.log \
  --prompt "Analyze response times, identify bottlenecks, create optimization recommendations" \
  --output performance_analysis.md
```

### Report Generation

```bash
# Sales data
cerebrate-file sales_data.txt \
  --file_prompt report_template.md \
  --prompt "Generate quarterly sales report with trends, visualizations descriptions, and recommendations" \
  --output Q4_report.md

# Technical debt
cerebrate-file codebase_analysis.txt \
  --prompt "Generate technical debt report: categorize issues, estimate effort, prioritize fixes" \
  --output tech_debt_report.md
```

## Academic and Research

### Paper Formatting

```bash
# Academic style
cerebrate-file draft.md \
  --prompt "Format as academic paper: add abstract, improve citations, use formal language" \
  --output paper.md

# Add references
cerebrate-file research.md \
  --file_prompt bibliography.bib \
  --prompt "Add proper citations in APA format, create references section"
```

### Literature Review

```bash
# Extract key info
cerebrate-file ./papers \
  --recurse "**/*.txt" \
  --prompt "Extract: main hypothesis, methodology, key findings, limitations" \
  --output ./summaries/

# Compile review
cat summaries/*.md > all_summaries.md
cerebrate-file all_summaries.md \
  --prompt "Create comprehensive literature review with themes, gaps, and future directions" \
  --output literature_review.md
```

### Note Organization

```bash
# Structure notes
cerebrate-file scattered_notes.txt \
  --prompt "Organize into sections: Key Concepts, Methodologies, Findings, Questions" \
  --output organized_notes.md

# Study guide
cerebrate-file lecture_notes.md \
  --prompt "Create study guide: key terms with definitions, important formulas, practice questions" \
  --output study_guide.md
```

## Creative Projects

### Story Development

```bash
# Character profiles
cerebrate-file character_sketches.txt \
  --prompt "Expand character profiles: add backstory, motivations, character arcs" \
  --temp 0.9 \
  --output characters.md

# Better dialogue
cerebrate-file story.md \
  --data_format semantic \
  --prompt "Improve dialogue: make it more natural, add subtext, vary speech patterns" \
  --temp 0.8
```

### Content Expansion

```bash
# Blog post
cerebrate-file outline.md \
  --prompt "Expand each point into 2-3 paragraphs with examples and transitions" \
  --max_tokens_ratio 200 \
  --output full_post.md

# Course material
cerebrate-file course_outline.md \
  --prompt "Expand into full course: add learning objectives, exercises, quizzes for each module" \
  --output course_content.md
```

## DevOps and Configuration

### Configuration Generation

```bash
# Docker setup
cerebrate-file app_requirements.txt \
  --prompt "Generate Dockerfile and docker-compose.yml for Python web application" \
  --output docker_configs.md

# CI/CD pipeline
cerebrate-file project_info.md \
  --prompt "Generate GitHub Actions workflow for Python project with tests, linting, and deployment" \
  --output .github/workflows/ci.yml
```

### Documentation from Code

```bash
# Terraform docs
cerebrate-file ./terraform \
  --recurse "**/*.tf" \
  --prompt "Generate infrastructure documentation with resource descriptions and dependencies" \
  --output infrastructure.md

# Kubernetes docs
cerebrate-file ./k8s \
  --recurse "**/*.yaml" \
  --prompt "Document Kubernetes resources: purpose, configuration, relationships" \
  --output k8s_docs.md
```

## Batch Processing Examples

### Sequential Processing

```bash
#!/bin/bash
# process_sequential.sh

for file in *.md; do
  echo "Processing $file..."
  cerebrate-file "$file" \
    --file_prompt standard_prompt.md \
    --output "processed/${file}"
  sleep 2
done
```

### Parallel Processing

```bash
# GNU parallel
find . -name "*.txt" | parallel -j 4 \
  cerebrate-file {} --output processed/{/}

# Built-in parallel
cerebrate-file . \
  --recurse "**/*.md" \
  --workers 8 \
  --file_prompt instructions.md \
  --output ./processed/
```

### Conditional Processing

```bash
#!/bin/bash
# smart_process.sh

for file in *.md; do
  size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file")

  if [ $size -lt 10000 ]; then
    chunk_size=16000
  elif [ $size -lt 100000 ]; then
    chunk_size=32000
  else
    chunk_size=48000
  fi

  cerebrate-file "$file" \
    --chunk_size $chunk_size \
    --output "processed/${file}"
done
```

## Complex Workflows

### Multi-Stage Processing

```bash
#!/bin/bash
# multi_stage.sh

# Stage 1: Clean data
cerebrate-file raw_data.txt \
  --prompt "Extract relevant information, fix formatting" \
  --output stage1.md

# Stage 2: Analyze
cerebrate-file stage1.md \
  --prompt "Analyze patterns, identify trends, add insights" \
  --output stage2.md

# Stage 3: Report
cerebrate-file stage2.md \
  --file_prompt report_template.md \
  --prompt "Format as executive report with recommendations" \
  --output final_report.md
```

### Content Pipeline

```bash
#!/bin/bash
# content_pipeline.sh

SOURCE_DIR="content/drafts"
EDIT_DIR="content/edited"
TRANS_DIR="content/translated"
FINAL_DIR="content/final"

# Edit content
cerebrate-file "$SOURCE_DIR" \
  --recurse "**/*.md" \
  --prompt "Improve clarity, fix grammar, enhance structure" \
  --output "$EDIT_DIR" \
  --workers 4

# Translate
cerebrate-file "$EDIT_DIR" \
  --recurse "**/*.md" \
  --prompt "Translate to Spanish, preserve formatting" \
  --output "$TRANS_DIR" \
  --workers 4

# Final format
cerebrate-file "$TRANS_DIR" \
  --recurse "**/*.md" \
  --prompt "Add table of contents, improve headings, check links" \
  --output "$FINAL_DIR" \
  --workers 4
```

## Tips for Examples

1. **Start small**: Test with small files first
2. **Use dry run**: Verify chunking before processing
3. **Save prompts**: Reuse successful instruction files
4. **Monitor progress**: Use verbose mode for debugging
5. **Tune parameters**: Adjust based on results
6. **Handle errors**: Add error checking to scripts
7. **Document workflows**: Save successful commands
8. **Version control**: Track changes in processed files

## Next Steps

- See [CLI Reference](cli-reference/) for all options
- Review [Configuration](configuration/) for optimization
- Check [Troubleshooting](troubleshooting/) for issues
- Explore [API Reference](api-reference/) for automation