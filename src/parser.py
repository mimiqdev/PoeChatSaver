"""
Parser module for extracting conversation data from Poe.com HTML.

This module handles:
- Parsing conversation messages from HTML
- Extracting metadata (title, bot name, etc.)
- Identifying message senders and content
- Handling different message types and formats
"""

import re
import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup, Tag
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a single message in the conversation."""
    sender: str              # Sender name (user or bot name)
    content: str             # Message content
    message_type: str        # 'user' or 'bot'
    timestamp: Optional[str] = None  # Timestamp if available
    raw_html: Optional[str] = None   # Original HTML for debugging


@dataclass
class ConversationData:
    """Represents the complete conversation data."""
    title: str
    messages: List[Message]
    bot_name: str
    conversation_id: str
    source_url: str
    extracted_at: str
    metadata: Dict[str, Any]


class ConversationParser:
    """Parses Poe.com conversation HTML and extracts structured data."""
    
    def __init__(self):
        """Initialize the parser."""
        self.bot_patterns = [
            r'Bot image for (.+)',
            r'@(.+) on Poe',
            r'Go to @(.+) on Poe'
        ]
    
    def parse_conversation(self, soup: BeautifulSoup, source_url: str = "", conversation_id: str = "") -> ConversationData:
        """
        Parse the complete conversation from BeautifulSoup object.
        
        Args:
            soup: Parsed HTML content
            source_url: Original URL
            conversation_id: Conversation ID
            
        Returns:
            ConversationData object with all extracted information
        """
        try:
            # Extract metadata
            metadata = self.extract_metadata(soup)
            
            # Extract messages
            messages = self.extract_messages(soup)
            
            # Determine bot name from messages or metadata
            bot_name = self._determine_bot_name(messages, metadata)
            
            # Extract title
            title = self._extract_title(soup, messages)
            
            conversation_data = ConversationData(
                title=title,
                messages=messages,
                bot_name=bot_name,
                conversation_id=conversation_id,
                source_url=source_url,
                extracted_at=datetime.now().isoformat(),
                metadata=metadata
            )
            
            logger.info(f"Parsed conversation with {len(messages)} messages")
            return conversation_data
            
        except Exception as e:
            logger.error(f"Error parsing conversation: {e}")
            raise
    
    def extract_messages(self, soup: BeautifulSoup) -> List[Message]:
        """
        Extract all messages from the conversation.
        
        Args:
            soup: Parsed HTML content
            
        Returns:
            List of Message objects in chronological order
        """
        # First attempt: parse from Next.js embedded JSON (__NEXT_DATA__)
        try:
            messages = self._extract_messages_from_next_data(soup)
            if messages:
                logger.info(f"Extracted {len(messages)} messages from __NEXT_DATA__ JSON")
                return messages
        except Exception as e:
            logger.warning(f"Failed to parse messages from __NEXT_DATA__: {e}")

        # Second attempt: legacy text parsing (fallback)
        try:
            conversation_content = self._find_conversation_content(soup)
            if conversation_content:
                messages = self._parse_conversation_text(conversation_content)
            else:
                # Fallback: try to parse from all text content
                all_text = soup.get_text()
                messages = self._parse_fallback_text(all_text)

            logger.info(f"Extracted {len(messages)} messages using fallback parsers")
            return messages
        except Exception as e:
            logger.error(f"Error extracting messages with fallback parsers: {e}")
            return []

    def _extract_messages_from_next_data(self, soup: BeautifulSoup) -> List[Message]:
        """Extract messages from the __NEXT_DATA__ JSON payload if present."""
        script_tag = soup.find('script', id='__NEXT_DATA__')
        if script_tag and script_tag.string:
            json_str = script_tag.string
        else:
            # Fallback: try to find JSON via regex in the raw HTML
            html_str = str(soup)
            match = re.search(r'<script[^>]+id=["\"]__NEXT_DATA__["\"][^>]*>(.*?)</script>', html_str, re.DOTALL)
            if not match:
                return []
            json_str = match.group(1)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as exc:
            logger.warning(f"Failed to decode __NEXT_DATA__ JSON: {exc}")
            return []

        # Navigate to messages list safely
        messages_json = (
            data.get('props', {})
            .get('pageProps', {})
            .get('data', {})
            .get('mainQuery', {})
            .get('chatShare', {})
            .get('messages', [])
        )

        messages: List[Message] = []

        for msg in messages_json:
            try:
                # Content text
                text = msg.get('text', '').strip()
                # For JSON payload, assume content is valid unless empty
                if not text:
                    continue

                author_role = msg.get('author', '').lower()
                if author_role == 'human':
                    sender = 'user'
                    message_type = 'user'
                else:
                    # Prefer displayName if available
                    author_bot = msg.get('authorBot') or {}
                    sender = (
                        author_bot.get('displayName')
                        or author_bot.get('handle')
                        or author_role
                    )
                    message_type = 'bot'

                # Attempt to convert timestamp (creationTime appears in microseconds)
                ts_raw = msg.get('creationTime')
                timestamp_iso = None
                if isinstance(ts_raw, (int, float)):
                    try:
                        timestamp_iso = datetime.fromtimestamp(ts_raw / 1e6).isoformat()
                    except Exception:
                        timestamp_iso = str(ts_raw)

                messages.append(
                    Message(
                        sender=sender,
                        content=text,
                        message_type=message_type,
                        timestamp=timestamp_iso,
                    )
                )
            except Exception as msg_exc:
                logger.warning(f"Skipping malformed message JSON: {msg_exc}")

        return messages
    
    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract metadata from the page.
        
        Args:
            soup: Parsed HTML content
            
        Returns:
            Dictionary containing metadata
        """
        metadata = {}
        
        try:
            # Extract page title
            title_tag = soup.find('title')
            if title_tag:
                metadata['page_title'] = title_tag.get_text().strip()
            
            # Look for meta tags
            meta_description = soup.find('meta', attrs={'name': 'description'})
            if meta_description:
                metadata['description'] = meta_description.get('content', '')
            
            # Look for bot information in text
            page_text = soup.get_text()
            
            # Try to find bot mentions
            bot_matches = []
            for pattern in self.bot_patterns:
                matches = re.findall(pattern, page_text)
                bot_matches.extend(matches)
            
            if bot_matches:
                metadata['mentioned_bots'] = list(set(bot_matches))
            
            # Look for "Shared conversation" indicator
            if "Shared conversation" in page_text:
                metadata['is_shared_conversation'] = True
            
            logger.debug(f"Extracted metadata: {metadata}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {}
    
    def _find_conversation_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Find the main conversation content in the HTML."""
        try:
            # Look for common patterns that might contain conversation
            text_content = soup.get_text()
            
            # Check if there's a "Shared conversation" section
            if "Shared conversation" in text_content:
                # Split on this marker and take content after it
                parts = text_content.split("Shared conversation")
                if len(parts) > 1:
                    # Remove navigation and footer content
                    content = parts[1]
                    
                    # Remove common footer patterns
                    footer_patterns = [
                        "Continue chat",
                        "New chat",
                        "Go to @",
                        "About · Blog · Careers"
                    ]
                    
                    for pattern in footer_patterns:
                        if pattern in content:
                            content = content.split(pattern)[0]
                    
                    return content.strip()
            
            return text_content
            
        except Exception as e:
            logger.error(f"Error finding conversation content: {e}")
            return None
    
    def _parse_conversation_text(self, text: str) -> List[Message]:
        """Parse messages from conversation text content."""
        messages = []
        
        try:
            # Split text into lines and process
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            current_message = None
            current_content = []
            
            for line in lines:
                # Skip empty lines and navigation elements
                if not line or line in ['ShareSign up', 'Continue chat', 'New chat']:
                    continue
                
                # Skip lines that appear to be corrupted
                if not self._is_valid_content(line):
                    logger.warning(f"Skipping potentially corrupted line: {line[:50]}...")
                    continue
                
                # Check if this line indicates a bot message
                bot_match = self._extract_bot_name_from_line(line)
                if bot_match:
                    # Save previous message if exists
                    if current_message and current_content:
                        content = '\n'.join(current_content).strip()
                        if content and self._is_valid_content(content):
                            current_message.content = content
                            messages.append(current_message)
                    
                    # Start new bot message
                    current_message = Message(
                        sender=bot_match,
                        content="",
                        message_type="bot"
                    )
                    current_content = []
                    continue
                
                # Check if this might be a user message (heuristic)
                if current_message is None and not self._is_navigation_or_metadata(line):
                    # This might be a user message - validate it first
                    if self._is_valid_content(line):
                        current_message = Message(
                            sender="User",
                            content="",
                            message_type="user"
                        )
                        current_content = [line]
                elif current_message and not self._is_navigation_or_metadata(line):
                    # Continue current message
                    current_content.append(line)
            
            # Add the last message
            if current_message and current_content:
                content = '\n'.join(current_content).strip()
                if content and self._is_valid_content(content):
                    current_message.content = content
                    messages.append(current_message)
            
            # Filter out any remaining messages with corrupted content
            valid_messages = []
            for message in messages:
                if message.content and self._is_valid_content(message.content):
                    valid_messages.append(message)
                else:
                    logger.warning(f"Filtered out corrupted message from {message.sender}")
            
            return valid_messages
            
        except Exception as e:
            logger.error(f"Error parsing conversation text: {e}")
            return []
    
    def _parse_fallback_text(self, text: str) -> List[Message]:
        """Fallback method to parse messages from all text content."""
        # This is a simplified fallback - could be improved based on actual HTML structure
        messages = []
        
        # Try to identify message patterns
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for i, line in enumerate(lines):
            if not self._is_navigation_or_metadata(line) and len(line) > 10:
                # Assume it's either user or bot message
                message_type = "bot" if any(bot in line for bot in ['Bot', 'AI', 'Assistant']) else "user"
                
                message = Message(
                    sender="Bot" if message_type == "bot" else "User",
                    content=line,
                    message_type=message_type
                )
                messages.append(message)
        
        return messages
    
    def _extract_bot_name_from_line(self, line: str) -> Optional[str]:
        """Extract bot name from a line if it contains bot information."""
        for pattern in self.bot_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        return None
    
    def _is_navigation_or_metadata(self, line: str) -> bool:
        """Check if a line is navigation or metadata rather than conversation content."""
        navigation_patterns = [
            'Explore', 'Create', 'Send feedback', 'Poe - Fast AI Chat',
            'Download', 'Follow us', 'About', 'Blog', 'Careers', 'Help center',
            'Privacy policy', 'Terms of service', 'Continue chat', 'New chat',
            'ShareSign up', 'Shared conversation'
        ]
        
        return any(pattern.lower() in line.lower() for pattern in navigation_patterns)
    
    def _determine_bot_name(self, messages: List[Message], metadata: Dict[str, Any]) -> str:
        """Determine the bot name from messages or metadata."""
        # Try to find bot name from messages
        for message in messages:
            if message.message_type == "bot" and message.sender != "Bot":
                return message.sender
        
        # Try to find from metadata
        if 'mentioned_bots' in metadata and metadata['mentioned_bots']:
            return metadata['mentioned_bots'][0]
        
        return "Unknown Bot"
    
    def _extract_title(self, soup: BeautifulSoup, messages: List[Message]) -> str:
        """Extract conversation title."""
        # Try to get from page title
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            # Clean up common patterns
            if ' - Poe' in title:
                title = title.replace(' - Poe', '')
            if title and title != 'Poe' and self._is_valid_title(title):
                return title
        
        # Fallback to first user message
        for message in messages:
            if message.message_type == "user" and message.content:
                # Validate that content is not corrupted
                if self._is_valid_content(message.content):
                    # Use first 100 characters as title
                    title = message.content[:100]
                    if len(message.content) > 100:
                        title += "..."
                    return title
        
        # If no valid content found, use conversation ID or default
        return "Untitled Conversation"
    
    def _is_valid_title(self, title: str) -> bool:
        """Check if a title contains valid text and not corrupted data."""
        if not title or len(title.strip()) == 0:
            return False
        
        # Check for excessive non-printable characters (indicator of corruption)
        printable_chars = sum(1 for c in title if c.isprintable())
        total_chars = len(title)
        
        if total_chars == 0:
            return False
        
        printable_ratio = printable_chars / total_chars
        
        # If less than 70% of characters are printable, likely corrupted
        if printable_ratio < 0.7:
            return False
        
        # Check for excessive special characters that suggest binary data
        special_char_count = sum(1 for c in title if ord(c) > 127 and not c.isalnum())
        if special_char_count > len(title) * 0.5:  # More than 50% special chars
            return False
        
        return True
    
    def _is_valid_content(self, content: str) -> bool:
        """Check if content appears to be valid text and not corrupted data."""
        if not content or len(content.strip()) == 0:
            return False
        
        # Check for reasonable printable character ratio
        printable_chars = sum(1 for c in content if c.isprintable() or c.isspace())
        total_chars = len(content)
        
        if total_chars == 0:
            return False
        
        printable_ratio = printable_chars / total_chars
        
        # If less than 80% of characters are printable, likely corrupted
        if printable_ratio < 0.8:
            return False
        
        # Check for patterns that suggest corrupted data
        # Look for excessive sequences of non-ASCII characters
        non_ascii_sequences = re.findall(r'[^\x00-\x7F]{10,}', content)
        if len(non_ascii_sequences) > 3:  # More than 3 long non-ASCII sequences
            return False
        
        # Check for control characters that shouldn't be in normal text
        control_chars = sum(1 for c in content if ord(c) < 32 and c not in '\n\r\t')
        if control_chars > len(content) * 0.1:  # More than 10% control chars
            return False
        
        return True 