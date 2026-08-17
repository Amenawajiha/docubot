"""
Document Reader Factory - Main entry point for document text extraction.

This module provides a single, unified interface for
extracting text from various document formats.

Usage:
    reader = DocumentReader()
    text = reader.extract(file_bytes, "document.pdf")
"""

from pathlib import Path
from typing import Type

from .base_reader import BaseReader


class DocumentReader:
    """
    Factory class for routing documents to format-specific readers.
    
    Uses lazy loading - reader classes are imported only when needed,
    reducing startup time and memory usage for unused formats.
    """
    
    # Maps file extensions to reader class paths (lazy loading)
    EXTENSION_MAP: dict[str, tuple[str, str]] = {
        ".pdf": ("pdf_reader", "PDFReader"),
        ".epub": ("epub_reader", "EPUBReader"),
        ".docx": ("docx_reader", "DOCXReader"),
        ".pptx": ("pptx_reader", "PPTXReader"),  
        ".xlsx": ("xlsx_reader", "XLSXReader"),
        ".csv": ("xlsx_reader", "CSVReader"),
        ".txt": ("txt_reader", "TextReader"),
        ".md": ("md_reader", "MarkdownReader"),
        ".png": ("image_reader", "ImageReader"),
        ".jpg": ("image_reader", "ImageReader"),
        ".jpeg": ("image_reader", "ImageReader"),
        ".webp": ("image_reader", "ImageReader"),
        ".tiff": ("image_reader", "ImageReader"),
        ".bmp": ("image_reader", "ImageReader"),
    }
    
    def __init__(self):
        """Initialize the factory with an empty reader cache."""
        self._reader_cache: dict[str, BaseReader] = {}
    
    def extract(self, file_bytes: bytes, filename: str) -> str:
        """
        Extract plain text from a file.
        
        Args:
            file_bytes: Raw bytes of the file
            filename: Filename (used to determine format)
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If file extension is not supported or file is empty
            RuntimeError: If extraction fails
        """
        if not file_bytes:
            raise ValueError(f"Empty file provided: {filename}")
        
        reader = self._get_reader(filename)
        return reader.extract(file_bytes)
    
    @property
    def supported_extensions(self) -> list[str]:
        """Return all supported file extensions."""
        return sorted(self.EXTENSION_MAP.keys())
    
    def _get_reader(self, filename: str) -> BaseReader:
        """
        Get or create a reader for the given filename.
        
        Implements lazy loading and caching:
        1. Determine extension
        2. Check cache for existing reader instance
        3. If not cached, dynamically import and instantiate
        4. Cache for future use
        
        Args:
            filename: Filename to extract extension from
            
        Returns:
            Reader instance for this file type
            
        Raises:
            ValueError: If extension is not supported
        """
        ext = Path(filename).suffix.lower()
        
        # Validate extension
        if ext not in self.EXTENSION_MAP:
            supported = ", ".join(self.supported_extensions)
            raise ValueError(
                f"Unsupported file extension '{ext}'. "
                f"Supported formats: {supported}"
            )
        
        # Return cached reader if available
        if ext in self._reader_cache:
            return self._reader_cache[ext]
        
        # Lazy import and instantiate reader
        module_path, class_name = self.EXTENSION_MAP[ext]
        reader_class = self._import_reader_class(module_path, class_name)
        reader_instance = reader_class()
        
        # Cache for future use
        self._reader_cache[ext] = reader_instance
        
        return reader_instance
    
    @staticmethod
    def _import_reader_class(module_path: str, class_name: str) -> Type[BaseReader]:
        """
        Dynamically import a reader class.
        
        Args:
            module_path: Full module path (e.g., 'ingestion.reader.pdf_reader')
            class_name: Class name to import (e.g., 'PDFReader')
            
        Returns:
            Reader class (not instance)
            
        Raises:
            ImportError: If module or class cannot be imported
        """
        try:
            from importlib import import_module
            module = import_module(f"src.ingestion.reader.{module_path}")
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Failed to import {class_name} from {module_path}: {e}"
            ) from e