# Prompt Library

This directory contains pre-configured prompts for common use cases with `cerebrate-file`.

## Available Prompts

### fix-pdf-extracted-text.xml
**Purpose**: Clean up poorly extracted PDF text
**Usage**: `cerebrate-file input.txt --file-prompt fix-pdf-extracted-text.xml`

This prompt helps clean up text that was poorly extracted from PDFs, fixing:
- Hard hyphenation at line endings (e.g., "docu-\nment" → "document")
- Page numbers, headers, and footers
- OCR errors and character substitution issues
- Paragraph breaks and formatting artifacts
- Converts to clean Markdown format

## Using Prompts from the Library

You can reference prompts from this library in three ways:

1. **By name only** (recommended for library prompts):
   ```bash
   cerebrate-file input.txt --file-prompt fix-pdf-extracted-text.xml
   ```

2. **By absolute path** (for custom prompts):
   ```bash
   cerebrate-file input.txt --file-prompt /path/to/custom-prompt.xml
   ```

3. **By relative path** (for project-specific prompts):
   ```bash
   cerebrate-file input.txt --file-prompt ./prompts/my-prompt.xml
   ```

## Adding Custom Prompts

To add your own prompts to the library:

1. Create your prompt file with any extension (`.xml`, `.txt`, `.md`, etc.)
2. Place it in this directory
3. It will be available by name after reinstalling the package

## Prompt Format

Prompts can be in any text format. The POML (Prompt Optimization Markup Language) format used in `fix-pdf-extracted-text.xml` provides structured instructions, but plain text prompts work just as well.

## Combining with Text Prompts

You can combine library prompts with additional instructions:

```bash
cerebrate-file input.txt \
  --file-prompt fix-pdf-extracted-text.xml \
  --prompt "Also translate to Spanish"
```

The file prompt is loaded first, followed by the text prompt.