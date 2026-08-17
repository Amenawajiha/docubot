"""
Text Readers - Extract text from plain text and Markdown files.

Handles:
- TXT files with encoding detection
- Markdown files with syntax stripping
"""

import logging
import re

from .base_reader import BaseReader

logger = logging.getLogger(__name__)


class TextReader(BaseReader):
    """
    Extract text from plain text files with automatic encoding detection.
    """
    
    @property
    def supported_extensions(self) -> list[str]:
        return [".txt"]
    
    def extract(self, file_bytes: bytes) -> str:
        """
        Extract text from TXT file.
        
        Args:
            file_bytes: Raw text file bytes
            
        Returns:
            Decoded text content
            
        Raises:
            ValueError: If file is empty
        """
        if not file_bytes:
            raise ValueError("Empty TXT file provided")
        
        # Detect encoding
        encoding = self._detect_encoding(file_bytes)
        
        try:
            content = file_bytes.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            logger.warning(f"Failed to decode with {encoding}, trying latin-1")
            content = file_bytes.decode('latin-1')
        
        # Remove BOM if present
        content = content.lstrip('\ufeff')
        
        if not content.strip():
            raise ValueError("TXT file is empty")
        
        return content
    
    @staticmethod
    def _detect_encoding(file_bytes: bytes) -> str:
        """
        Detect encoding of text file.
        
        Args:
            file_bytes: Raw bytes
            
        Returns:
            Detected encoding string
        """
        try:
            import chardet
            detected = chardet.detect(file_bytes)
            encoding = detected.get('encoding', 'utf-8')
            confidence = detected.get('confidence', 0)
            
            if confidence < 0.7:
                logger.warning(
                    f"Low confidence ({confidence:.2f}) in encoding detection, "
                    f"using utf-8"
                )
                return 'utf-8'
            
            return encoding
        
        except ImportError:
            logger.info("chardet not available, defaulting to utf-8")
            return 'utf-8'
