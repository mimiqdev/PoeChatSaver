"""
Utility functions for PoeChat Saver.

This module provides:
- File handling utilities
- URL processing functions
- Validation helpers
- Common utility functions
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize a string to be safe for use as a filename.
    
    Args:
        filename: The original filename
        max_length: Maximum length for the filename
        
    Returns:
        Sanitized filename safe for filesystem use
    """
    if not filename:
        return "untitled"
    
    # Check if filename appears to be corrupted/binary data
    if not _is_valid_filename_content(filename):
        logger.warning("Detected potentially corrupted filename, using fallback")
        return "corrupted_conversation"
    
    # Remove or replace invalid characters
    # Invalid characters for most filesystems: / \ : * ? " < > |
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters and other problematic characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    
    # Replace excessive non-ASCII characters with underscores to avoid encoding issues
    # Keep some non-ASCII for international characters but limit excessive sequences
    filename = re.sub(r'[^\x00-\x7F]{5,}', '_', filename)
    
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Remove any remaining problematic characters
    filename = re.sub(r'[^\w\s\-_\.\u4e00-\u9fff\u3400-\u4dbf]', '_', filename)
    
    # Limit length
    if len(filename) > max_length:
        filename = filename[:max_length-3] + "..."
    
    # Ensure it's not empty after cleaning
    result = filename if filename and len(filename.strip()) > 0 else "untitled"
    
    # Final validation
    if not _is_valid_filename_content(result):
        return "untitled"
    
    return result


def _is_valid_filename_content(content: str) -> bool:
    """Check if content is suitable for use as a filename."""
    if not content or len(content.strip()) == 0:
        return False
    
    # Check for reasonable printable character ratio
    printable_chars = sum(1 for c in content if c.isprintable())
    total_chars = len(content)
    
    if total_chars == 0:
        return False
    
    printable_ratio = printable_chars / total_chars
    
    # If less than 80% of characters are printable, likely corrupted
    if printable_ratio < 0.8:
        return False
    
    # Check for excessive special characters
    special_chars = sum(1 for c in content if not (c.isalnum() or c.isspace() or c in '-_. '))
    if special_chars > len(content) * 0.3:  # More than 30% special chars
        return False
    
    return True


def generate_unique_filename(base_filename: str, directory: str = ".", extension: str = ".md") -> str:
    """
    Generate a unique filename by adding numbers if file exists.
    
    Args:
        base_filename: Base filename without extension
        directory: Directory to check for existing files
        extension: File extension to add
        
    Returns:
        Unique filename that doesn't exist in the directory
    """
    # Sanitize the base filename
    clean_filename = sanitize_filename(base_filename)
    
    # Ensure extension starts with dot
    if not extension.startswith('.'):
        extension = '.' + extension
    
    # Create full path
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    
    filename = clean_filename + extension
    filepath = directory / filename
    
    # If file doesn't exist, use it
    if not filepath.exists():
        return str(filepath)
    
    # Add numbers until we find a unique name
    counter = 1
    while True:
        filename = f"{clean_filename}_{counter}{extension}"
        filepath = directory / filename
        
        if not filepath.exists():
            return str(filepath)
        
        counter += 1
        
        # Safety check to prevent infinite loop
        if counter > 9999:
            raise RuntimeError(f"Cannot generate unique filename for {base_filename}")


def extract_conversation_id_from_url(url: str) -> Optional[str]:
    """
    Extract conversation ID from Poe share URL.
    
    Args:
        url: Poe share URL
        
    Returns:
        Conversation ID or None if not found
    """
    try:
        parsed = urlparse(url)
        # Extract ID from path like '/s/vtYxbVcTZH5pVoi166Lr'
        match = re.match(r'^/s/([a-zA-Z0-9_-]+)$', parsed.path)
        if match:
            return match.group(1)
    except Exception as e:
        logger.error(f"Error extracting conversation ID from {url}: {e}")
    
    return None


def read_urls_from_file(filepath: str) -> List[str]:
    """
    Read URLs from a text file (one URL per line).
    
    Args:
        filepath: Path to file containing URLs
        
    Returns:
        List of URLs found in the file
    """
    urls = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Basic URL validation
                if line.startswith('http'):
                    urls.append(line)
                else:
                    logger.warning(f"Line {line_num} in {filepath} doesn't look like a URL: {line}")
        
        logger.info(f"Read {len(urls)} URLs from {filepath}")
        return urls
        
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return []
    except Exception as e:
        logger.error(f"Error reading URLs from {filepath}: {e}")
        return []


def ensure_directory_exists(directory: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path to create
        
    Returns:
        True if directory exists or was created successfully
    """
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {e}")
        return False


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.2 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def validate_output_path(output_path: str) -> bool:
    """
    Validate if output path is writable.
    
    Args:
        output_path: Path to validate
        
    Returns:
        True if path is valid and writable
    """
    try:
        # Check if directory is writable
        directory = os.path.dirname(output_path) or '.'
        
        if not os.path.exists(directory):
            # Try to create directory
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Test write access
        test_file = os.path.join(directory, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return True
        except:
            return False
            
    except Exception as e:
        logger.error(f"Error validating output path {output_path}: {e}")
        return False


def count_words_in_content(content: str) -> int:
    """
    Count words in text content.
    
    Args:
        content: Text content to count
        
    Returns:
        Number of words
    """
    if not content:
        return 0
    
    # Simple word counting - split on whitespace
    words = content.split()
    return len(words)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix 