"""
PoeChat Saver - A tool to save Poe.com shared conversations as markdown files.

This package provides functionality to:
- Scrape Poe.com shared conversation pages
- Parse conversation content and metadata
- Convert conversations to markdown format
- Save conversations as local files
"""

__version__ = "1.0.0"
__author__ = "PoeChat Saver"

from .scraper import PoePageScraper
from .parser import ConversationParser, Message
from .converter import MarkdownConverter

__all__ = [
    "PoePageScraper",
    "ConversationParser", 
    "Message",
    "MarkdownConverter",
] 