#!/usr/bin/env python3
# this_file: src/cerebrate_file/cli.py

"""CLI interface for cerebrate_file package.

This module provides the command-line interface using Fire,
orchestrating the document processing pipeline.
"""

import os
import sys
import time
from typing import Optional

from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
from loguru import logger

from .api_client import explain_metadata_with_llm
from .cerebrate_file import calculate_completion_budget, prepare_chunk_messages, process_document
from .chunking import create_chunks
from .config import setup_logging, validate_environment, validate_inputs, validate_recursive_inputs
from .constants import DEFAULT_CHUNK_SIZE
from .file_utils import (
    build_base_prompt,
    check_metadata_completeness,
    parse_frontmatter_content,
    read_file_safely,
    write_output_atomically,
)
from .models import ProcessingState, RateLimitStatus
from .tokenizer import encode_text
from .ui import FileProgressDisplay

__all__ = ["run"]


def run(
    input_data: str,
    output_data: Optional[str] = None,
    file_prompt: Optional[str] = None,
    prompt: Optional[str] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    max_tokens_ratio: int = 100,
    data_format: str = "markdown",
    sample_size: int = 200,
    temp: float = 0.7,
    top_p: float = 0.8,
    model: str = "qwen-3-coder-480b",
    verbose: bool = False,
    explain: bool = False,
    dry_run: bool = False,
    recurse: Optional[str] = None,
    workers: int = 4,
) -> None:
    """Process large documents by chunking for Cerebras qwen-3-coder-480b.

    Args:
        input_data: Path to input file to process, or directory when using --recurse
        output_data: Output file path (default: overwrite input_data), or directory when using --recurse
        file_prompt: Path to file containing initial instructions
        prompt: Freeform instruction text to append after file_prompt
        chunk_size: Target maximum input chunk size in tokens (default: 32000)
        max_tokens_ratio: Completion budget as % of chunk size (default: 100)
        data_format: Chunking strategy - text|semantic|markdown|code (default: markdown)
        sample_size: Number of tokens for continuity examples (default: 200)
        temp: Model temperature (default: 0.7)
        top_p: Model top-p (default: 0.8)
        model: Model name override (default: qwen-3-coder-480b)
        verbose: Enable debug logging (default: False)
        explain: Enable metadata processing with frontmatter parsing (default: False)
        dry_run: Perform chunking and display results without making API calls (default: False)
        recurse: Glob pattern for recursive file processing (e.g., "*.md", "**/*.txt")
        workers: Number of parallel workers for recursive processing (default: 4)
    """
    # Load environment variables
    load_dotenv()

    # Setup logging first
    setup_logging(verbose)
    text_prompt = prompt

    # Always print input file path
    print(f"Processing: {input_data}")

    logger.info(f"cerebrate-file starting - processing {input_data}")
    logger.debug(
        f"Parameters: chunk_size={chunk_size}, format={data_format}, "
        f"sample_size={sample_size}, model={model}"
    )

    # Validate environment and inputs
    validate_environment()

    # Check if we're in recursive mode
    if recurse is not None:
        # Recursive processing mode - validate recursive parameters
        validate_recursive_inputs(input_data, recurse, workers, output_data)

        # Implement recursive processing
        from pathlib import Path
        from .recursive import find_files_recursive, replicate_directory_structure, process_files_parallel
        from .ui import MultiFileProgressDisplay

        input_path = Path(input_data)
        output_path = Path(output_data) if output_data else None

        print(f"🔄 Starting recursive processing with pattern '{recurse}'")
        print(f"📁 Input directory: {input_path}")
        print(f"👥 Workers: {workers}")

        if output_path:
            print(f"📁 Output directory: {output_path}")
        else:
            print(f"📁 Output: In-place (overwrite input files)")

        # Find all matching files
        file_pairs = find_files_recursive(input_path, recurse, output_path)

        if not file_pairs:
            print("⚠️  No files found matching the pattern")
            return

        print(f"📊 Found {len(file_pairs)} files to process")

        # Create output directory structure if needed
        if output_path:
            replicate_directory_structure(file_pairs)

        # If dry-run, just show what would be processed
        if dry_run:
            print("\n🔍 DRY-RUN MODE - Files that would be processed:")
            for input_file, output_file in file_pairs[:10]:
                print(f"  {input_file} -> {output_file}")
            if len(file_pairs) > 10:
                print(f"  ... and {len(file_pairs) - 10} more files")
            return

        # Set up multi-file progress display
        progress_display = MultiFileProgressDisplay() if not verbose else None

        if progress_display:
            progress_display.start_overall_processing(len(file_pairs))

        # Build base prompt once for all files
        base_prompt, base_prompt_tokens = build_base_prompt(file_prompt, text_prompt)

        # Define processing function for each file
        def process_file_wrapper(input_file: Path, output_file: Path):
            """Process a single file."""
            from .models import ProcessingState

            try:
                # Read file content
                input_content = read_file_safely(str(input_file))

                # Handle frontmatter parsing and metadata processing for --explain mode
                metadata = {}
                content_to_chunk = input_content

                if explain:
                    # Parse frontmatter
                    metadata, content_to_chunk = parse_frontmatter_content(input_content)
                    logger.info(
                        f"Frontmatter parsed for {input_file}: {len(metadata)} fields, {len(content_to_chunk)} content chars"
                    )

                    # Check metadata completeness
                    is_complete, missing_fields = check_metadata_completeness(metadata)

                    if not is_complete:
                        # Create chunks first to get the first chunk for explanation
                        temp_chunks = create_chunks(content_to_chunk, data_format, chunk_size)

                        if temp_chunks:
                            # Initialize Cerebras client for explanation
                            try:
                                client = Cerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))

                                # Generate missing metadata
                                generated_metadata = explain_metadata_with_llm(
                                    client=client,
                                    existing_metadata=metadata,
                                    first_chunk_text=temp_chunks[0].text,
                                    model=model,
                                    temp=temp,
                                    top_p=top_p,
                                )

                                # Update metadata with generated fields
                                if generated_metadata:
                                    metadata.update(generated_metadata)
                                    logger.info(
                                        f"Metadata updated for {input_file} with generated fields: {list(generated_metadata.keys())}"
                                    )
                                else:
                                    logger.warning(f"No metadata generated by LLM for {input_file}")

                            except Exception as e:
                                logger.error(f"Failed to generate metadata for {input_file}: {e}")

                        chunks = temp_chunks
                    else:
                        chunks = create_chunks(content_to_chunk, data_format, chunk_size)
                else:
                    # Create chunks normally when not in explain mode
                    chunks = create_chunks(content_to_chunk, data_format, chunk_size)

                if not chunks:
                    logger.warning(f"No chunks created for {input_file}")
                    return ProcessingState()

                # Initialize client (reuse if already created for metadata)
                if not explain or 'client' not in locals():
                    client = Cerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))

                # Start progress for this file if display available
                if progress_display:
                    progress_display.start_file(str(input_file), str(output_file), len(chunks))

                # Create progress callback for this file
                def file_progress_callback(chunks_done: int, remaining_calls: int):
                    if progress_display:
                        progress_display.update_file_progress(str(input_file), chunks_done, remaining_calls)

                # Process document
                output_text, state = process_document(
                    client=client,
                    chunks=chunks,
                    base_prompt=base_prompt,
                    base_prompt_tokens=base_prompt_tokens,
                    model=model,
                    temp=temp,
                    top_p=top_p,
                    max_tokens_ratio=max_tokens_ratio,
                    sample_size=sample_size,
                    metadata=metadata if explain else None,
                    verbose=verbose,
                    progress_callback=file_progress_callback if progress_display else None,
                )

                # Write output
                write_output_atomically(output_text, str(output_file), metadata if explain else None)

                # Finish progress for this file
                if progress_display:
                    progress_display.finish_file(str(input_file))

                return state

            except Exception as e:
                logger.error(f"Error processing {input_file}: {e}")
                if progress_display:
                    progress_display.finish_file(str(input_file))
                raise

        # Process files in parallel
        result = process_files_parallel(
            file_pairs,
            process_file_wrapper,
            workers,
            None  # Progress handled internally
        )

        # Finish overall progress
        if progress_display:
            progress_display.finish_overall_processing()

        # Show summary
        print(f"\n📊 Processing Summary:")
        print(f"  ✅ Successful: {len(result.successful)} files")
        if result.failed:
            print(f"  ❌ Failed: {len(result.failed)} files")
            for failed_file, error in result.failed[:5]:  # Show first 5 failures
                print(f"     - {failed_file}: {error}")
            if len(result.failed) > 5:
                print(f"     ... and {len(result.failed) - 5} more failures")

        if result.successful:
            print(f"  📝 Total tokens: {result.total_input_tokens:,} input, {result.total_output_tokens:,} output")
            print(f"  ⏱️  Total time: {result.total_time:.1f}s")

        logger.info(f"Recursive processing complete: {len(result.successful)} successful, {len(result.failed)} failed")
        return

    # Single file processing mode - existing logic
    validate_inputs(input_data, chunk_size, sample_size, max_tokens_ratio, data_format)

    # Set output path
    if output_data is None:
        output_data = input_data
        logger.info(
            f"No output_data specified, will overwrite input file: {input_data}"
        )
    else:
        logger.info(f"Output will be written to: {output_data}")

    # Build base prompt
    if verbose:
        print(f"🔧 Setting up processing...")
    base_prompt, base_prompt_tokens = build_base_prompt(file_prompt, text_prompt)
    if verbose:
        print(f"  → Base prompt: {base_prompt_tokens} tokens")

    # Read input content
    input_content = read_file_safely(input_data)
    if verbose:
        print(f"📄 Loaded: {len(input_content):,} characters")
    logger.info(f"Input loaded: {len(input_content)} characters")

    # Handle frontmatter parsing and metadata processing for --explain mode
    metadata = {}
    content_to_chunk = input_content

    if explain:
        if verbose:
            print("🔍 Parsing frontmatter...")

        # Parse frontmatter
        metadata, content_to_chunk = parse_frontmatter_content(input_content)
        logger.info(
            f"Frontmatter parsed: {len(metadata)} fields, {len(content_to_chunk)} content chars"
        )

        if metadata and verbose:
            print(f"📋 Metadata found: {list(metadata.keys())}")

        # Check metadata completeness
        is_complete, missing_fields = check_metadata_completeness(metadata)

        if not is_complete:
            if verbose:
                print(f"⚠️  Missing metadata fields: {missing_fields}")

            # Create chunks first to get the first chunk for explanation
            temp_chunks = create_chunks(content_to_chunk, data_format, chunk_size)

            if temp_chunks:
                if verbose:
                    print("🤖 Generating missing metadata with LLM...")

                # Skip metadata explanation in dry-run mode
                if dry_run:
                    if verbose:
                        print("  → Skipping metadata generation (dry-run mode)")
                    generated_metadata = {}
                else:
                    # Initialize Cerebras client for explanation
                    try:
                        client = Cerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))

                        # Generate missing metadata
                        generated_metadata = explain_metadata_with_llm(
                            client=client,
                            existing_metadata=metadata,
                            first_chunk_text=temp_chunks[0].text,
                            model=model,
                            temp=temp,
                            top_p=top_p,
                        )

                        # Update metadata with generated fields
                        if generated_metadata:
                            metadata.update(generated_metadata)
                            logger.info(
                                f"Metadata updated with generated fields: {list(generated_metadata.keys())}"
                            )
                            if verbose:
                                print(
                                    f"✅ Generated metadata: {list(generated_metadata.keys())}"
                                )
                        else:
                            logger.warning("No metadata generated by LLM")

                    except Exception as e:
                        logger.error(f"Failed to generate metadata: {e}")
                        if verbose:
                            print(f"❌ Metadata generation failed: {e}")
        else:
            if verbose:
                print("✅ All required metadata fields present, skipping explanation")

    # Create chunks (use already-created chunks if we did explanation, otherwise create new)
    if explain and "temp_chunks" in locals():
        chunks = temp_chunks
        if verbose:
            print(f"✂️  Using chunks from metadata processing...")
            print(f"ℹ️  All chunks (including first) will be processed with the normal prompt")
    else:
        if verbose:
            print(f"✂️  Creating chunks using {data_format} mode...")
        chunks = create_chunks(content_to_chunk, data_format, chunk_size)

    if not chunks:
        print("⚠️  No chunks created - input may be empty")
        logger.warning("No chunks created - input may be empty")
        write_output_atomically("", output_data, metadata if explain else None)
        return

    if verbose:
        print(
            f"📦 Created {len(chunks)} chunks (avg: {sum(c.token_count for c in chunks) // len(chunks):,} tokens each)"
        )
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            print(f"  → Chunk {i + 1}: {chunk.token_count:,} tokens")
        if len(chunks) > 3:
            print(f"  → ... and {len(chunks) - 3} more chunks")

        print(f"\n🚀 Starting processing with {model}...")

    # If dry-run mode, display chunk analysis and exit
    if dry_run:
        _show_dry_run_analysis(
            chunks,
            data_format,
            base_prompt,
            base_prompt_tokens,
            sample_size,
            max_tokens_ratio,
            metadata if explain else None,
        )
        return

    # Initialize Cerebras client (only if not dry-run)
    try:
        client = Cerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))
        logger.debug("Cerebras client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Cerebras client: {e}")
        sys.exit(1)

    # Set up progress display (only for non-verbose mode)
    progress_display = None
    progress_callback = None

    if not verbose:
        progress_display = FileProgressDisplay()
        progress_display.start_file_processing(input_data, output_data, len(chunks))

        def update_progress(chunks_completed: int, remaining_calls: int):
            progress_display.update_progress(chunks_completed, remaining_calls)

        progress_callback = update_progress

    # Process all chunks
    final_output, state = process_document(
        client=client,
        chunks=chunks,
        base_prompt=base_prompt,
        base_prompt_tokens=base_prompt_tokens,
        model=model,
        temp=temp,
        top_p=top_p,
        max_tokens_ratio=max_tokens_ratio,
        sample_size=sample_size,
        metadata=metadata if explain else None,
        verbose=verbose,
        progress_callback=progress_callback,
    )

    # Finish progress display
    if progress_display:
        progress_display.finish_file_processing()

    # Write output atomically
    write_output_atomically(final_output, output_data, metadata if explain else None)

    # Show remaining daily requests from the last chunk's rate limit headers
    last_rate_status = state.last_rate_status
    if last_rate_status.headers_parsed and last_rate_status.requests_remaining is not None:
        # Show remaining daily requests from rate limit headers
        print(f"📊 Remaining today: {last_rate_status.requests_remaining} requests")

        # If we're getting close to the limit, show a warning
        if last_rate_status.requests_limit > 0:
            usage_percent = ((last_rate_status.requests_limit - last_rate_status.requests_remaining)
                           / last_rate_status.requests_limit * 100)
            if usage_percent > 80:
                print(f"⚠️  Daily quota {usage_percent:.1f}% used")

    # Show final statistics only in verbose mode
    if verbose:
        print(f"\n📊 Processing Summary:")
        print(f"  • Time: {state.processing_time:.1f}s")
        print(f"  • Chunks: {state.chunks_processed}/{len(chunks)} processed")
        print(f"  • Input tokens: {state.total_input_tokens:,}")
        print(f"  • Output tokens: {state.total_output_tokens:,}")
        print(f"  • Output size: {len(final_output):,} characters")
        print(
            f"  • Average chunk size: {state.total_input_tokens // len(chunks) if chunks else 0:,} tokens"
        )
        print(
            f"  • Average response size: {state.total_output_tokens // state.chunks_processed if state.chunks_processed else 0:,} tokens"
        )
        print(
            f"  • Processing rate: {state.total_input_tokens / state.processing_time:.0f} tokens/second"
        )
        print(f"  • File updated: {output_data}")

    # Log final statistics
    logger.info(f"Processing complete in {state.processing_time:.1f}s")
    logger.info(f"Total input tokens: {state.total_input_tokens}")
    logger.info(f"Total output tokens: {state.total_output_tokens}")
    logger.info(f"Chunks processed: {state.chunks_processed}/{len(chunks)}")
    logger.info(f"Output written to: {output_data}")


def _show_dry_run_analysis(
    chunks,
    data_format: str,
    base_prompt: str,
    base_prompt_tokens: int,
    sample_size: int,
    max_tokens_ratio: int,
    metadata,
) -> None:
    """Show dry-run analysis output."""
    print("\n🔍 DRY-RUN MODE - No API calls will be made\n")

    # Display chunk analysis
    print(f"📊 Chunking Analysis:")
    print(f"  • Chunking mode: {data_format}")
    print(f"  • Total chunks: {len(chunks)}")
    print(f"  • Total input tokens: {sum(c.token_count for c in chunks):,}")
    print(
        f"  • Average chunk size: {sum(c.token_count for c in chunks) // len(chunks):,} tokens"
    )
    print(f"  • Max chunk size: {max(c.token_count for c in chunks):,} tokens")
    print(f"  • Min chunk size: {min(c.token_count for c in chunks):,} tokens")

    # Show sample of what would be sent for each chunk
    print(f"\n📋 Sample API Request Structure:")

    for i, chunk in enumerate(chunks[:2]):  # Show first 2 chunks as samples
        print(f"\n── Chunk {i + 1}/{len(chunks)} ──")

        # Build sample messages
        continuity_block = ""
        if i > 0 and sample_size > 0:
            # Simulate continuity from previous chunk
            continuity_block = "[Continuity context would be added here]"

        messages, total_tokens = prepare_chunk_messages(
            base_prompt,
            chunk,
            continuity_block,
            base_prompt_tokens,
            metadata,
        )

        print(f"  Input tokens: {total_tokens}")
        print(
            f"  Max completion tokens: {calculate_completion_budget(chunk.token_count, max_tokens_ratio)}"
        )

        # Show message structure
        print(f"  Messages structure:")
        print(f"    • System prompt: {base_prompt_tokens} tokens")
        if metadata:
            import json
            print(
                f"    • Metadata context: {len(encode_text(json.dumps(metadata, separators=(',', ':'))))} tokens"
            )
        if continuity_block:
            print(f"    • Continuity context: {sample_size} tokens (estimated)")
        print(f"    • User content: {chunk.token_count} tokens")

        # Show preview of chunk content
        preview_lines = chunk.text.split("\n")[:5]
        preview = "\n".join(preview_lines)
        if len(preview) > 200:
            preview = preview[:200] + "..."
        print(f"\n  Chunk preview:")
        for line in preview.split("\n"):
            print(f"    │ {line}")

        if i == 1:
            print(f"\n  [... {len(chunks) - 2} more chunks would follow ...]")
            break

    # Summary
    print(f"\n✅ Dry-run complete - no API calls were made")
    print(f"   Total estimated API calls: {len(chunks)}")
    print(
        f"   Estimated total input tokens: {sum(c.token_count for c in chunks) + len(chunks) * base_prompt_tokens:,}"
    )