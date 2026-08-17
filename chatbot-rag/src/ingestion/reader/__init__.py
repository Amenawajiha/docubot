"""
Document Reader Package

Provides a unified interface for extracting text from various document formats.

Usage:
    from src.ingestion.reader import DocumentReader
    
    reader = DocumentReader()
    text = reader.extract(file_bytes, "document.pdf")
"""

from .base import DocumentReader
from .base_reader import BaseReader

__all__ = ['DocumentReader', 'BaseReader']