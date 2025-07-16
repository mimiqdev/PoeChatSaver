"""
Markdown conversion module for Poe conversations.

This module handles:
- Converting conversation data to markdown format
- Formatting messages with proper headers and styling
- Adding metadata and source information
- Handling special content (code blocks, links, etc.)
"""

import re
import logging
from typing import List, Dict, Any
from datetime import datetime
from .parser import ConversationData, Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarkdownConverter:
    """Converts conversation data to markdown format."""
    
    def __init__(self, include_metadata: bool = True, include_footer: bool = True):
        """
        Initialize the converter.
        
        Args:
            include_metadata: Whether to include metadata in output
            include_footer: Whether to include footer information
        """
        self.include_metadata = include_metadata
        self.include_footer = include_footer
    
    def convert_conversation(self, conversation: ConversationData) -> str:
        """
        Convert conversation data to markdown format.
        
        Args:
            conversation: ConversationData object to convert
            
        Returns:
            Formatted markdown string
        """
        try:
            markdown_parts = []
            
            # Add title
            title = self._clean_title(conversation.title)
            markdown_parts.append(f"# {title}\n")
            
            # Add metadata if enabled
            if self.include_metadata:
                metadata_section = self._format_metadata(conversation)
                if metadata_section:
                    markdown_parts.append(metadata_section)
            
            # Add separator
            markdown_parts.append("---\n")
            
            # Add conversation content header
            markdown_parts.append("## 对话内容\n")
            
            # Convert messages
            for message in conversation.messages:
                message_md = self._format_message(message, conversation.bot_name)
                if message_md:
                    markdown_parts.append(message_md)
            
            # Add footer if enabled
            if self.include_footer:
                footer = self._format_footer(conversation)
                if footer:
                    markdown_parts.append("---\n")
                    markdown_parts.append(footer)
            
            result = "\n".join(markdown_parts)
            logger.info("Successfully converted conversation to markdown")
            return result
            
        except Exception as e:
            logger.error(f"Error converting conversation to markdown: {e}")
            raise
    
    def _format_metadata(self, conversation: ConversationData) -> str:
        """Format metadata section."""
        metadata_lines = []
        
        # Basic information
        if conversation.source_url:
            metadata_lines.append(f"**来源**: {conversation.source_url}")
        
        if conversation.bot_name and conversation.bot_name != "Unknown Bot":
            metadata_lines.append(f"**AI模型**: {conversation.bot_name}")
        
        if conversation.conversation_id:
            metadata_lines.append(f"**对话ID**: {conversation.conversation_id}")
        
        if conversation.extracted_at:
            try:
                # Format the timestamp nicely
                dt = datetime.fromisoformat(conversation.extracted_at.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%Y年%m月%d日 %H:%M:%S")
                metadata_lines.append(f"**导出时间**: {formatted_time}")
            except:
                metadata_lines.append(f"**导出时间**: {conversation.extracted_at}")
        
        # Additional metadata
        if conversation.metadata:
            if 'page_title' in conversation.metadata and conversation.metadata['page_title']:
                page_title = conversation.metadata['page_title']
                if page_title != conversation.title:
                    metadata_lines.append(f"**页面标题**: {page_title}")
        
        message_count = len(conversation.messages)
        user_messages = len([m for m in conversation.messages if m.message_type == "user"])
        bot_messages = len([m for m in conversation.messages if m.message_type == "bot"])
        metadata_lines.append(f"**消息数量**: {message_count} ({user_messages} 用户, {bot_messages} AI)")
        
        if metadata_lines:
            return "\n".join(metadata_lines) + "\n"
        
        return ""
    
    def _format_message(self, message: Message, bot_name: str) -> str:
        """Format a single message."""
        try:
            # Clean content
            content = self._clean_content(message.content)
            if not content:
                return ""
            
            # Format based on message type
            if message.message_type == "user":
                header = "### 👤 用户"
            else:
                # Use specific bot name if available
                display_name = message.sender if message.sender and message.sender != "Bot" else bot_name
                if display_name == "Unknown Bot":
                    display_name = "AI助手"
                header = f"### 🤖 {display_name}"
            
            # Format content with proper indentation
            formatted_content = self._format_content(content)
            
            return f"{header}\n{formatted_content}\n"
            
        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return f"### ❌ 格式化错误\n无法格式化消息内容\n"
    
    def _clean_title(self, title: str) -> str:
        """Clean and format the title."""
        if not title:
            return "未命名对话"
        
        # Remove common patterns
        title = title.replace("Poe - Fast AI Chat", "").strip()
        title = title.replace(" - Poe", "").strip()
        
        # Remove excessive whitespace
        title = re.sub(r'\s+', ' ', title)
        
        # Limit length
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title or "未命名对话"
    
    def _clean_content(self, content: str) -> str:
        """Clean message content."""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        content = content.strip()
        
        # Remove common navigation elements that might have leaked in
        navigation_patterns = [
            r'ShareSign up',
            r'Continue chat',
            r'New chat',
            r'Go to @\w+ on Poe',
            r'Bot image for \w+'
        ]
        
        for pattern in navigation_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _format_content(self, content: str) -> str:
        """Format content with proper markdown styling."""
        if not content:
            return ""
        
        # Handle code blocks (detect by common patterns)
        if self._looks_like_code(content):
            # Try to detect language
            language = self._detect_language(content)
            return f"```{language}\n{content}\n```"
        
        # Handle YAML content specifically
        if content.strip().startswith('yaml') or 'nodes:' in content or 'edges:' in content:
            return f"```yaml\n{content}\n```"
        
        # Handle regular content
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append("")
                continue
            
            # Handle different content types
            if line.startswith('Copy'):
                # Skip "Copy" buttons
                continue
            elif self._is_list_item(line):
                # Format as markdown list
                if not line.startswith('-') and not line.startswith('*'):
                    line = f"- {line}"
            
            formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _looks_like_code(self, content: str) -> bool:
        """Detect if content looks like code."""
        code_indicators = [
            '{', '}', '[', ']', '()', '=>', '==', '!=',
            'function', 'def ', 'class ', 'import ', 'from ',
            '```', 'console', 'bash', 'python', 'javascript',
            'nodes:', 'edges:', 'source:', 'target:'
        ]
        
        content_lower = content.lower()
        indicator_count = sum(1 for indicator in code_indicators if indicator in content_lower)
        
        # If multiple code indicators present, likely code
        return indicator_count >= 2
    
    def _detect_language(self, content: str) -> str:
        """Try to detect programming language."""
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ['def ', 'import ', 'class ', 'print(']):
            return 'python'
        elif any(keyword in content_lower for keyword in ['function', 'const ', 'let ', 'var ']):
            return 'javascript'
        elif any(keyword in content_lower for keyword in ['nodes:', 'edges:', 'source:', 'target:']):
            return 'yaml'
        elif any(keyword in content_lower for keyword in ['bash', 'shell', '$', 'cd ', 'ls ', 'mkdir']):
            return 'bash'
        elif content_lower.startswith('yaml'):
            return 'yaml'
        
        return ''
    
    def _is_list_item(self, line: str) -> bool:
        """Check if a line should be formatted as a list item."""
        # Already formatted
        if line.startswith(('-', '*', '+')):
            return False
        
        # Look for patterns that suggest list items
        list_patterns = [
            r'^\d+\.',  # Numbered lists
            r'^[A-Z]\)',  # Lettered lists
            r'^•',  # Bullet points
        ]
        
        for pattern in list_patterns:
            if re.match(pattern, line):
                return True
        
        return False
    
    def _format_footer(self, conversation: ConversationData) -> str:
        """Format footer information."""
        footer_lines = []
        
        # Add generation info
        footer_lines.append("*本对话由 PoeChat Saver 工具导出*")
        
        # Add additional info if available
        if conversation.source_url:
            footer_lines.append(f"*原始链接: {conversation.source_url}*")
        
        return '\n'.join(footer_lines) 