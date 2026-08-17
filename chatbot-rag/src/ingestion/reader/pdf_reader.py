"""
PDF Reader - Extract text from PDF files with intelligent OCR fallback.

Supports two extraction modes:
1. Text-based PDFs: Direct text extraction (fast, accurate)
2. Scanned/Image PDFs: Per-page OCR fallback (automatic detection)

Key features:
- Per-page evaluation (mixed text/scanned PDFs handled correctly)
- Garbled text detection (CID placeholders, PUA characters)
- Smart OCR fallback only for problematic pages
- Lazy loading of heavy dependencies
"""

import logging
import re
from io import BytesIO
from typing import Optional, TYPE_CHECKING

from .base_reader import BaseReader

logger = logging.getLogger(__name__)

# Minimum characters to consider a page successfully extracted
_PAGE_TEXT_MIN_CHARS = 10

# Regex for pdfminer's CID placeholder pattern, e.g. "(cid:123)"
_CID_PATTERN = re.compile(r"\(cid\s*:\s*\d+\s*\)")

# If >= 30% of non-whitespace chars are PUA/replacement chars, treat as garbled
_PUA_RATIO_THRESHOLD = 0.30

if TYPE_CHECKING:
    import fitz

class PDFReader(BaseReader):
    """
    Extract text from PDF files with intelligent per-page OCR fallback.
    
    This reader is smarter than simple OCR fallback - it evaluates each page
    individually and only OCRs pages that need it, handling mixed PDFs
    (some pages text, some scanned) efficiently.
    """
    
    @property
    def supported_extensions(self) -> list[str]:
        return [".pdf"]
    
    def extract(self, file_bytes: bytes) -> str:
        """
        Extract text from PDF file.
        
        Flow:
        1. Try pdfplumber text extraction page by page
        2. Evaluate each page for quality (length, garbled text)
        3. OCR only pages that are short or garbled
        4. Combine all pages
        
        Args:
            file_bytes: Raw PDF bytes
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If no text is found after all extraction attempts
            RuntimeError: If PDF processing fails
        """
        if not file_bytes:
            raise ValueError("Empty PDF file provided")
        
        # Extract with per-page smart fallback
        page_texts = self._extract_with_pdfplumber(file_bytes)
        
        # Combine pages
        content = "\n\n".join(t.strip() for t in page_texts if t and t.strip())
        
        if not content:
            raise ValueError(
                "No text could be extracted from PDF "
                "(tried pdfplumber and OCR per page)"
            )
        
        logger.info(f"PDF extraction complete: {len(content)} characters")
        return content
    
    def _extract_with_pdfplumber(self, file_bytes: bytes) -> list[str]:
        """
        Extract text page by page with intelligent OCR fallback.
        
        Args:
            file_bytes: Raw PDF bytes
            
        Returns:
            List of page texts (one per page)
            
        Raises:
            RuntimeError: If pdfplumber fails
        """
        # Lazy import
        try:
            import pdfplumber
        except ImportError as e:
            raise RuntimeError(
                "pdfplumber is required for PDF support. "
                "Install with: pip install pdfplumber"
            ) from e
        
        pdf_doc = None  # Lazy convert PDF to images only if needed
        page_texts: list[str] = []
        
        try:
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                total_pages = len(pdf.pages)
                
                for idx, page in enumerate(pdf.pages):
                    # Try text extraction
                    extracted = (page.extract_text() or "").strip()
                    
                    # Evaluate quality
                    is_garbled = self._is_garbled(extracted)
                    too_short = len(extracted) < _PAGE_TEXT_MIN_CHARS
                    
                    # ponytail: skip OCR if the page has literally no text and no images (it's blank)
                    if not extracted and not page.images:
                        logger.info(f"PDF page {idx + 1}/{total_pages}: blank page skipped")
                        continue

                    # Decide: use extracted text or OCR fallback
                    if too_short or is_garbled:
                        logger.info(
                            f"PDF page {idx + 1}/{total_pages}: "
                            f"OCR fallback (chars={len(extracted)}, garbled={is_garbled})"
                        )
                        
                        ocr_text, pdf_doc = self._fallback_ocr(
                            file_bytes=file_bytes,
                            page_index=idx,
                            pdf_doc=pdf_doc,
                        )
                        page_texts.append(ocr_text)
                    else:
                        logger.info(
                            f"PDF page {idx + 1}/{total_pages}: "
                            f"pdfplumber extracted {len(extracted)} chars"
                        )
                        page_texts.append(extracted)
        
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise RuntimeError(f"Failed to read PDF: {e}") from e
        
        finally:
            if pdf_doc is not None:
                try:
                    pdf_doc.close()
                except Exception:
                    pass
        
        return page_texts
    
    def _fallback_ocr(
        self,
        file_bytes: bytes,
        page_index: int,
        pdf_doc: Optional["fitz.Document"] = None,
    ) -> tuple[str, Optional["fitz.Document"]]:
        """
        OCR a single PDF page.
        
        Converts the entire PDF to images once (if not already done),
        then caches for subsequent page OCRs.
        
        Args:
            file_bytes: Raw PDF bytes
            page_index: Zero-based page index to OCR
            pdf_doc: Cached fitz Document (None = open now)
            
        Returns:
            Tuple of (page_text, pdf_doc_cache)
        """
        # Lazy imports
        try:
            import fitz
        except ImportError as e:
            raise RuntimeError(
                "PyMuPDF is required for PDF OCR fallback. "
                "Install the 'pymupdf' package (for example: pip install pymupdf)."
            ) from e
        
        try:
            from ..utils.ocr import run_ocr
        except ImportError as e:
            raise RuntimeError(
                "OCR utility not found. Ensure src/ingestion/utils/ocr.py exists."
            ) from e
        
        if pdf_doc is None:
            logger.info("Opening PDF with PyMuPDF for OCR rendering...")
            pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        page = pdf_doc.load_page(page_index)

        zoom = 300 / 72
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        img_bytes = pix.tobytes("png")
        page_text = run_ocr(img_bytes)
        
        return page_text.strip(), pdf_doc
    
    def _is_garbled(self, text: str) -> bool:
        """
        Detect garbled text using two strategies.
        
        Strategy 1: CID placeholders like "(cid:123)"
        - Strong signal that pdfminer couldn't extract proper Unicode
        
        Strategy 2: High ratio of Private Use Area (PUA) characters
        - PUA characters (U+E000-F8FF, etc.) indicate encoding issues
        - Unicode replacement character (U+FFFD) indicates decoding failure
        
        Args:
            text: Extracted text to evaluate
            
        Returns:
            True if text appears garbled
        """
        if not text or not text.strip():
            return False
        
        # Strategy 1: CID pattern is immediate disqualifier
        if _CID_PATTERN.search(text):
            logger.debug("Garbled text detected: CID placeholders found")
            return True
        
        # Strategy 2: Count PUA and replacement characters
        total_chars = 0
        pua_count = 0
        
        for ch in text:
            if ch.isspace():
                continue
            
            total_chars += 1
            codepoint = ord(ch)
            
            # Check if character is in PUA ranges or is replacement char
            if (
                0xE000 <= codepoint <= 0xF8FF       # BMP PUA
                or 0xF0000 <= codepoint <= 0xFFFFF   # Supplementary PUA-A
                or 0x100000 <= codepoint <= 0x10FFFF # Supplementary PUA-B
                or codepoint == 0xFFFD               # Replacement character
            ):
                pua_count += 1
        
        if total_chars == 0:
            return False
        
        ratio = pua_count / total_chars
        
        if ratio >= _PUA_RATIO_THRESHOLD:
            logger.debug(
                f"Garbled text detected: {ratio:.1%} PUA/replacement chars "
                f"(threshold: {_PUA_RATIO_THRESHOLD:.0%})"
            )
            return True
        
        return False