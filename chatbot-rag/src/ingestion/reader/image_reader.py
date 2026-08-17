"""
Image Reader - Extract text from images using OCR.

Supports: PNG, JPG, JPEG, WEBP, TIFF, BMP
"""

import logging

from .base_reader import BaseReader

logger = logging.getLogger(__name__)


class ImageReader(BaseReader):
    
    @property
    def supported_extensions(self) -> list[str]:
        return [".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"]
    
    def extract(self, file_bytes: bytes) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            file_bytes: Raw image bytes
            
        Returns:
            OCR-extracted text
            
        Raises:
            ValueError: If no text is found in the image
            RuntimeError: If OCR processing fails
        """
        if not file_bytes:
            raise ValueError("Empty image file provided")
        
        # Lazy import OCR utility
        try:
            from src.ingestion.utils.ocr import get_ocr_engine
        except ImportError as e:
            raise RuntimeError(
                "OCR utility not found. Ensure the OCR module is available."
            ) from e
        
        try:
            ocr_engine = get_ocr_engine(languages=['en'])
            text = ocr_engine.extract_text(file_bytes, preprocessing=True)
            
            if not text.strip():
                raise RuntimeError("Failed to extract text from image: No text content found")
            
            return text
        
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            raise RuntimeError(f"Failed to extract text from image: {e}") from e