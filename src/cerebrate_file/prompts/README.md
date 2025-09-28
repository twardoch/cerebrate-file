# Prompt Library

This directory contains pre-configured prompts for common use cases with `cerebrate-file`.

## Available Prompts

### fix-pdf-extracted-text.xml
**Purpose**: Clean up poorly extracted PDF text  
**Usage**: `cerebrate-file input.txt --file-prompt fix-pdf-extracted-text.xml`

Fixes common PDF extraction issues:
- Line-ending hyphens (e.g., "docu-\nment" → "document")
- Page numbers, headers, footers
- OCR errors and character substitutions
- Broken paragraph formatting
- Outputs clean Markdown

## Using Prompts

Reference prompts in three ways:

1. **By name** (for library prompts):
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

Add your own prompts to the library:

1. Create your prompt file with any extension (`.xml`, `.txt`, `.md`, etc.)
2. Place it in this directory
3. Reinstall the package to make it available by name

## Prompt Format

Prompts can be any text format. The POML format used in `fix-pdf-extracted-text.xml` provides structured instructions, but plain text works fine too.

## Combining Prompts

Combine library prompts with additional instructions:

```bash
cerebrate-file input.txt \
  --file-prompt fix-pdf-extracted-text.xml \
  --prompt "Also translate to Spanish"
```

The file prompt loads first, then the text prompt.