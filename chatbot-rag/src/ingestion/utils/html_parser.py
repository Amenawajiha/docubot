"""
HTML Parser Utility - Extract clean text from HTML/XHTML content.

This is a shared utility used by EPUB reader and potentially other readers
that need to parse HTML-based formats.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class HTMLParser:
    """
    Extract clean, readable text from HTML/XHTML documents.
    
    Removes boilerplate (scripts, styles, navigation) and preserves
    the semantic structure of the content.
    """
    
    def extract_text(self, html_bytes: bytes, encoding: Optional[str] = None) -> str:
        """
        Extract plain text from HTML bytes.
        
        Args:
            html_bytes: Raw HTML/XHTML bytes
            encoding: Optional encoding hint (auto-detected if None)
            
        Returns:
            Extracted plain text with preserved paragraph structure
            
        Raises:
            RuntimeError: If BeautifulSoup is not installed or parsing fails
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError as e:
            raise RuntimeError(
                "BeautifulSoup4 is required for HTML parsing. "
                "Install with: pip install beautifulsoup4"
            ) from e
        
        try:
            # Decode bytes to string
            if encoding:
                html_str = html_bytes.decode(encoding, errors='replace')
            else:
                # Try UTF-8 first, fall back to auto-detection
                try:
                    html_str = html_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    html_str = self._decode_with_detection(html_bytes)
            
            # Parse HTML
            soup = BeautifulSoup(html_str, 'html.parser')
            
            # Remove non-content elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            
            # Extract text with basic structure preservation
            text = soup.get_text(separator='\n', strip=True)
            
            # Clean up excessive whitespace while preserving paragraph breaks
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            return '\n\n'.join(lines)
        
        except Exception as e:
            logger.error(f"Failed to parse HTML: {e}")
            raise RuntimeError(f"HTML parsing failed: {e}") from e
    
    @staticmethod
    def _decode_with_detection(html_bytes: bytes) -> str:
        """
        Detect encoding and decode HTML bytes.
        
        Args:
            html_bytes: Raw HTML bytes
            
        Returns:
            Decoded string
        """
        try:
            import chardet
            detected = chardet.detect(html_bytes)
            encoding = detected.get('encoding', 'utf-8')
            confidence = detected.get('confidence', 0)
            
            if confidence < 0.7:
                logger.warning(
                    f"Low confidence ({confidence:.2f}) in detected encoding: {encoding}"
                )
                encoding = 'utf-8'
            
            return html_bytes.decode(encoding, errors='replace')
        
        except ImportError:
            logger.warning("chardet not available, falling back to latin-1")
            return html_bytes.decode('latin-1', errors='replace')