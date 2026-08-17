"""
Abstract base class for document readers.
 
"""

from abc import ABC, abstractmethod

class BaseReader(ABC):
    """    
    Each reader extracts plain text from a specific file format.
    Concrete implementations handle format-specific parsing logic.
    """
    @abstractmethod
    def extract(self, file_bytes: bytes) -> str:
        """
        Extract plain text content from file bytes.
        
        Args:
            file_bytes: Raw bytes of the document file
            
        Returns:
            Extracted text as a string
            
        Raises:
            ValueError: If file is empty or contains no extractable text
            RuntimeError: If extraction fails due to parsing errors
        """
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this reader supports."""
        pass