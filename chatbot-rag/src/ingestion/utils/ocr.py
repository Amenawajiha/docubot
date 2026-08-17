"""
OCR Utility - Optical Character Recognition for images and scanned documents.

Uses EasyOCR for text extraction from images. Shared by:
- Image reader (photos, diagrams, flowcharts)
- PDF reader (scanned/image-based PDFs)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OCREngine:
    """
    Optical Character Recognition using EasyOCR.
    
    This is a shared utility to avoid loading the OCR model multiple times.
    The reader instance is cached after first initialization.
    """
    
    def __init__(self, languages: Optional[list[str]] = None, gpu: bool = False):
        """
        Initialize OCR engine.
        
        Args:
            languages: List of language codes (default: ['en'])
            gpu: Use GPU acceleration if available (default: False)
        """
        self.languages = languages or ['en']
        self.gpu = gpu
        self._reader = None  # Lazy loaded
    
    def extract_text(self, image_bytes: bytes, preprocessing: bool = True) -> str:
        """
        Extract text from image bytes.
        
        Args:
            image_bytes: Raw image bytes (PNG, JPG, etc.)
            preprocessing: Apply preprocessing to improve OCR quality
            
        Returns:
            Extracted text content
            
        Raises:
            RuntimeError: If EasyOCR is not installed or OCR fails
        """
        # Lazy import and initialization
        if self._reader is None:
            self._reader = self._initialize_reader()
        
        try:
            # Load image
            image = self._load_image(image_bytes)
            
            # Optional preprocessing
            if preprocessing:
                image = self._preprocess_image(image)
            
            # Run OCR
            results = self._reader.readtext(image)
            
            # Extract text from results (EasyOCR returns list of (bbox, text, confidence))
            text_parts = [text for (bbox, text, confidence) in results if text.strip()]
            
            if not text_parts:
                logger.warning("No text detected in image")
                return ""
            
            # Join text parts with newlines (preserves structure)
            return '\n'.join(text_parts)
        
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise RuntimeError(f"Failed to extract text from image: {e}") from e
    
    def _initialize_reader(self):
        """
        Initialize EasyOCR reader (lazy loading).
        
        Returns:
            EasyOCR Reader instance
            
        Raises:
            RuntimeError: If EasyOCR cannot be imported
        """
        try:
            import easyocr
        except ImportError as e:
            raise RuntimeError(
                "EasyOCR is required for OCR functionality. "
                "Install with: pip install easyocr"
            ) from e
        
        logger.info(f"Initializing EasyOCR with languages: {self.languages}")
        
        try:
            reader = easyocr.Reader(
                self.languages,
                gpu=self.gpu,
                verbose=False
            )
            return reader
        except Exception as e:
            raise RuntimeError(f"Failed to initialize EasyOCR: {e}") from e
    
    @staticmethod
    def _load_image(image_bytes: bytes):
        """
        Load image from bytes into format suitable for EasyOCR.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            NumPy array in RGB format
        """
        try:
            from PIL import Image
            import numpy as np
            from io import BytesIO
        except ImportError as e:
            raise RuntimeError(
                "PIL and NumPy are required for image processing. "
                "Install with: pip install pillow numpy"
            ) from e
        
        # Load image
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB (EasyOCR expects RGB)
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        
        # Convert to NumPy array
        return np.array(image)
    
    @staticmethod
    def _preprocess_image(image):
        """
        Preprocess image to improve OCR quality.
        
        Applies:
        - Contrast enhancement
        - Sharpening
        - Binarization (for scanned documents)
        
        Args:
            image: NumPy array (RGB)
            
        Returns:
            Preprocessed NumPy array
        """
        try:
            from PIL import Image, ImageFilter, ImageEnhance
            import numpy as np
        except ImportError:
            logger.warning("PIL/NumPy not available, skipping preprocessing")
            return image
        
        # Convert NumPy array back to PIL Image for processing
        pil_image = Image.fromarray(image)
        
        # Convert to grayscale (better for text)
        pil_image = pil_image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(pil_image)
        pil_image = enhancer.enhance(2.0)
        
        # Sharpen
        pil_image = pil_image.filter(ImageFilter.SHARPEN)
        
        # Simple binarization
        arr = np.array(pil_image)
        threshold = arr.mean()
        arr = (arr > threshold).astype(np.uint8) * 255
        
        # Convert back to RGB for EasyOCR
        binarized = Image.fromarray(arr).convert('RGB')
        
        return np.array(binarized)


# Global cache/registry (this is the singleton - one cache managing all configs)
_ocr_engines: dict[tuple, OCREngine] = {}


def get_ocr_engine(languages: Optional[list[str]] = None, gpu: bool = False) -> OCREngine:
    """
    Get or create an OCR engine instance for the given configuration.
    
    Follows the Multiton pattern: a single global cache (singleton) manages 
    one OCREngine instance per (languages, gpu) configuration combination.
    
    This ensures:
    - No duplicate models loaded for the same configuration
    - Different configurations get isolated engine instances
    - No silent parameter loss
    
    Args:
        languages: List of language codes (default: ['en'])
        gpu: Use GPU acceleration if available
        
    Returns:
        OCREngine instance for the given configuration
    """
    global _ocr_engines
    
    # Normalize languages to tuple for use as dict key
    lang_key = tuple(languages or ['en'])
    cache_key = (lang_key, gpu)
    
    if cache_key not in _ocr_engines:
        logger.info(f"Creating OCR engine with languages={list(lang_key)}, gpu={gpu}")
        _ocr_engines[cache_key] = OCREngine(languages=languages, gpu=gpu)
    
    return _ocr_engines[cache_key]

def run_ocr(image_bytes: bytes, preprocessing: bool = True) -> str:
    """
    Convenience function for one-off OCR extraction.
    
    This is a simpler interface than get_ocr_engine() for readers
    that just need to OCR something quickly.
    
    Args:
        image_bytes: Raw image bytes (PNG, JPG, etc.)
        preprocessing: Apply preprocessing to improve quality
        
    Returns:
        Extracted text
    """
    engine = get_ocr_engine()
    return engine.extract_text(image_bytes, preprocessing=preprocessing)