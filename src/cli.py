"""
Command Line Interface for PoeChat Saver.

This module provides:
- CLI argument parsing
- Main application logic
- Progress reporting
- Error handling and user feedback
"""

import sys
import click
import logging
from pathlib import Path
from typing import List, Optional

from .scraper import PoePageScraper
from .parser import ConversationParser
from .converter import MarkdownConverter
from .utils import (
    sanitize_filename, generate_unique_filename, read_urls_from_file,
    ensure_directory_exists, validate_output_path, extract_conversation_id_from_url,
    format_file_size, count_words_in_content
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.command()
@click.argument('input_source', required=True)
@click.option('-o', '--output', 'output_path', 
              help='Output file path (for single URL) or directory (for multiple URLs)')
@click.option('-d', '--directory', 'output_dir', default='./conversations',
              help='Output directory for saved conversations (default: ./conversations)')
@click.option('--batch', is_flag=True,
              help='Treat input as file containing multiple URLs')
@click.option('--local-file', is_flag=True,
              help='Treat input as local HTML file instead of URL')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose logging')
@click.option('--no-metadata', is_flag=True,
              help='Exclude metadata from output')
@click.option('--no-footer', is_flag=True,
              help='Exclude footer from output')
@click.option('--timeout', default=30, type=int,
              help='Request timeout in seconds (default: 30)')
@click.option('--retries', default=3, type=int,
              help='Maximum retry attempts (default: 3)')
@click.option('--delay', default=1.0, type=float,
              help='Delay between requests in seconds (default: 1.0)')
def main(input_source: str, output_path: Optional[str], output_dir: str,
         batch: bool, local_file: bool, verbose: bool, no_metadata: bool, no_footer: bool,
         timeout: int, retries: int, delay: float):
    """
    PoeChat Saver - Save Poe.com shared conversations as markdown files.
    
    INPUT_SOURCE can be either:
    - A single Poe.com share URL (e.g., https://poe.com/s/ABC123)
    - A file containing multiple URLs (when using --batch flag)
    - A local HTML file (when using --local-file flag)
    
    Examples:
    
    \b
    # Save single conversation from URL
    poesaver "https://poe.com/s/vtYxbVcTZH5pVoi166Lr"
    
    \b
    # Save with custom filename
    poesaver "https://poe.com/s/vtYxbVcTZH5pVoi166Lr" -o "my_conversation.md"
    
    \b
    # Process local HTML file (useful for bypassing anti-bot protection)
    curl -s "https://poe.com/s/ABC123" -o page.html
    poesaver page.html --local-file
    
    \b
    # Batch process URLs from file
    poesaver urls.txt --batch -d ./my_conversations/
    
    \b
    # Verbose output
    poesaver "https://poe.com/s/vtYxbVcTZH5pVoi166Lr" --verbose
    """
    
    # Configure logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    try:
        # Initialize components
        scraper = PoePageScraper(timeout=timeout, max_retries=retries, delay=delay)
        parser = ConversationParser()
        converter = MarkdownConverter(
            include_metadata=not no_metadata,
            include_footer=not no_footer
        )
        
        # Handle local file processing
        if local_file:
            if not Path(input_source).exists():
                click.echo(f"❌ Local file not found: {input_source}", err=True)
                sys.exit(1)
            
            # Process local HTML file
            success_count = 0
            click.echo(f"🚀 Processing local HTML file: {input_source}")
            
            try:
                # Read local HTML file
                with open(input_source, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Parse HTML
                soup = scraper.extract_raw_html(html_content)
                
                # Try to extract URL from filename or use placeholder
                conversation_id = Path(input_source).stem
                source_url = f"file://{Path(input_source).absolute()}"
                
                conversation_data = parser.parse_conversation(soup, source_url, conversation_id)
                
                # Convert to markdown
                markdown_content = converter.convert_conversation(conversation_data)
                
                # Determine output file path
                if output_path:
                    output_file = output_path
                    if not output_file.endswith('.md'):
                        output_file += '.md'
                else:
                    base_filename = conversation_data.title or conversation_id
                    output_file = generate_unique_filename(base_filename, output_dir, '.md')
                
                # Save file
                output_directory = str(Path(output_file).parent)
                ensure_directory_exists(output_directory)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                # Report success
                file_size = len(markdown_content.encode('utf-8'))
                word_count = sum(count_words_in_content(msg.content) for msg in conversation_data.messages)
                
                click.echo(f"✅ Saved: {output_file}")
                click.echo(f"   📊 {len(conversation_data.messages)} messages, "
                          f"{word_count} words, {format_file_size(file_size)}")
                success_count = 1
                
            except Exception as e:
                click.echo(f"❌ Error processing local file: {e}", err=True)
                if verbose:
                    logger.error(f"Detailed error for {input_source}", exc_info=True)
                success_count = 0
            
            click.echo(f"\n🎉 Completed! {success_count}/1 files processed successfully.")
            return
        
        # Determine URLs to process (original logic for URLs)
        if batch:
            urls = read_urls_from_file(input_source)
            if not urls:
                click.echo(f"❌ No valid URLs found in {input_source}", err=True)
                sys.exit(1)
        else:
            urls = [input_source]
        
        # Validate URLs
        valid_urls = []
        for url in urls:
            if scraper.validate_url(url):
                valid_urls.append(url)
            else:
                click.echo(f"⚠️  Skipping invalid URL: {url}", err=True)
        
        if not valid_urls:
            click.echo("❌ No valid Poe share URLs found", err=True)
            sys.exit(1)
        
        # Process URLs
        success_count = 0
        total_count = len(valid_urls)
        
        click.echo(f"🚀 Processing {total_count} conversation(s)...")
        
        for i, url in enumerate(valid_urls, 1):
            try:
                click.echo(f"\n📥 [{i}/{total_count}] Fetching: {url}")
                
                # Extract conversation ID
                conversation_id = extract_conversation_id_from_url(url)
                
                # Fetch and parse
                html_content = scraper.fetch_page(url)
                soup = scraper.extract_raw_html(html_content)
                conversation_data = parser.parse_conversation(soup, url, conversation_id or "")
                
                # Convert to markdown
                markdown_content = converter.convert_conversation(conversation_data)
                
                # Determine output file path
                if total_count == 1 and output_path:
                    # Single file with specified path
                    output_file = output_path
                    if not output_file.endswith('.md'):
                        output_file += '.md'
                else:
                    # Generate filename from title
                    base_filename = conversation_data.title
                    output_file = generate_unique_filename(
                        base_filename, 
                        output_dir if batch or total_count > 1 else output_dir,
                        '.md'
                    )
                
                # Ensure output directory exists
                output_directory = str(Path(output_file).parent)
                if not ensure_directory_exists(output_directory):
                    click.echo(f"❌ Cannot create output directory: {output_directory}", err=True)
                    continue
                
                # Validate output path
                if not validate_output_path(output_file):
                    click.echo(f"❌ Cannot write to: {output_file}", err=True)
                    continue
                
                # Save file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                # Report success
                file_size = len(markdown_content.encode('utf-8'))
                word_count = sum(count_words_in_content(msg.content) for msg in conversation_data.messages)
                
                click.echo(f"✅ Saved: {output_file}")
                click.echo(f"   📊 {len(conversation_data.messages)} messages, "
                          f"{word_count} words, {format_file_size(file_size)}")
                
                success_count += 1
                
            except Exception as e:
                click.echo(f"❌ Error processing {url}: {e}", err=True)
                if verbose:
                    logger.exception(f"Detailed error for {url}")
                continue
        
        # Final summary
        click.echo(f"\n🎉 Completed! {success_count}/{total_count} conversations saved successfully.")
        
        if success_count < total_count:
            sys.exit(1)
            
    except KeyboardInterrupt:
        click.echo("\n⏹️  Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if verbose:
            logger.exception("Detailed error information")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            scraper.close()
        except:
            pass


@click.command('validate')
@click.argument('urls', nargs=-1, required=True)
def validate_command(urls):
    """Validate Poe share URLs without downloading."""
    scraper = PoePageScraper()
    
    click.echo(f"🔍 Validating {len(urls)} URL(s)...")
    
    valid_count = 0
    for url in urls:
        if scraper.validate_url(url):
            click.echo(f"✅ Valid: {url}")
            valid_count += 1
        else:
            click.echo(f"❌ Invalid: {url}")
    
    click.echo(f"\n📊 {valid_count}/{len(urls)} URLs are valid Poe share links")


@click.group()
def cli():
    """PoeChat Saver - Save Poe.com conversations as markdown files."""
    pass


# Add subcommands
cli.add_command(validate_command)


# For direct execution
if __name__ == '__main__':
    main() 