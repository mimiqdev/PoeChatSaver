"""
Web scraping module for Poe.com shared conversation pages.

This module handles:
- Fetching HTML content from Poe URLs
- Validating Poe share URLs
- Handling HTTP errors and retries
- Managing request headers and user agents
"""

import re
import time
import requests
import subprocess
import tempfile
import os
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PoePageScraper:
    """Handles scraping of Poe.com shared conversation pages."""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, delay: float = 1.0):
        """
        Initialize the scraper with configuration.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            delay: Delay between requests in seconds
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay
        self.session = requests.Session()
        
        # Set headers to better mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Cache-Control': 'max-age=0',
        })
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if the URL is a valid Poe.com share URL.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if valid Poe share URL, False otherwise
        """
        try:
            parsed = urlparse(url)
            
            # Check if it's a poe.com domain
            if parsed.netloc.lower() not in ['poe.com', 'www.poe.com']:
                return False
                
            # Check if it's a share URL (format: /s/[ID])
            path_pattern = r'^/s/[a-zA-Z0-9_-]+$'
            if not re.match(path_pattern, parsed.path):
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating URL {url}: {e}")
            return False
    
    def fetch_page(self, url: str) -> str:
        """
        Fetch the HTML content from a Poe share URL.
        
        Args:
            url: The Poe share URL to fetch
            
        Returns:
            Raw HTML content as string
            
        Raises:
            ValueError: If URL is invalid
            requests.RequestException: If request fails after retries
        """
        if not self.validate_url(url):
            raise ValueError(f"Invalid Poe share URL: {url}")
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching {url} (attempt {attempt + 1}/{self.max_retries})")
                
                # Add delay between requests
                if attempt > 0:
                    time.sleep(self.delay * attempt)
                
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                # Log response details for debugging
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                
                # Let requests handle decompression and encoding automatically
                html_content = response.text
                
                # Basic validation - check if we have reasonable content length
                if len(html_content) < 1000:
                    raise ValueError(f"Retrieved content too short for {url}: {len(html_content)} chars")
                
                # Check if we got an error page instead of actual content
                if "403" in html_content[:500] or "Access Denied" in html_content[:500]:
                    raise ValueError(f"Access denied by server for {url}")
                
                # Check for corrupted/garbled content (likely anti-bot response)
                # Look for excessive non-printable or unusual characters
                printable_ratio = sum(1 for c in html_content[:1000] if c.isprintable() or c.isspace()) / min(1000, len(html_content))
                if printable_ratio < 0.8:  # Less than 80% printable characters indicates corruption
                    raise ValueError(f"Received corrupted content from {url}. This is likely due to anti-bot protection. "
                                   f"Try manually saving the page: curl -s '{url}' -o page.html")
                
                # Check if we have valid HTML structure
                if not ("<html" in html_content.lower() and "</html>" in html_content.lower()):
                    raise ValueError(f"Invalid HTML structure received from {url}")
                
                logger.info(f"Successfully fetched {url}")
                return html_content
                
            except requests.RequestException as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
        # If all retries failed, raise the last exception
        raise requests.RequestException(f"Failed to fetch {url} after {self.max_retries} attempts") from last_exception
    
    def extract_raw_html(self, html: str) -> BeautifulSoup:
        """
        Parse HTML content and return BeautifulSoup object.
        
        Args:
            html: Raw HTML content
            
        Returns:
            BeautifulSoup parsed HTML object
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            return soup
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            # Fallback to html.parser if lxml fails
            return BeautifulSoup(html, 'html.parser')
    
    def extract_conversation_id(self, url: str) -> Optional[str]:
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
    
    def close(self):
        """Close the session."""
        self.session.close() 