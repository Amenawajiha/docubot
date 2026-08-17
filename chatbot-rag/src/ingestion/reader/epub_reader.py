"""
EPUB Reader - Extract text from EPUB (Electronic Publication) files.

1. Extracts the reading order from the OPF (Open Packaging Format) manifest
2. Reads each content document in spine order
3. Delegates HTML parsing to the shared HTML parser utility

"""

import logging
import zipfile
from io import BytesIO
from xml.etree import ElementTree

from .base_reader import BaseReader

logger = logging.getLogger(__name__)

# EPUB XML namespaces
_OPF_NS = "http://www.idpf.org/2007/opf"
_CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"

# Media types that contain readable content
_XHTML_MEDIA_TYPES = {"application/xhtml+xml", "text/html", "text/xml"}


class EPUBReader(BaseReader):
    """
    Extract text from EPUB files in proper reading order.
    
    EPUBs are structured archives with metadata defining the reading sequence.
    This reader respects that structure to maintain document coherence.
    """
    
    @property
    def supported_extensions(self) -> list[str]:
        return [".epub"]
    
    def extract(self, file_bytes: bytes) -> str:
        """
        Extract text from EPUB file.
        
        Args:
            file_bytes: Raw bytes of the EPUB file
            
        Returns:
            Concatenated text from all content documents in reading order
            
        Raises:
            ValueError: If EPUB is empty or contains no readable content
            RuntimeError: If EPUB structure is invalid or cannot be parsed
        """
        if not file_bytes:
            raise ValueError("Empty EPUB file provided")
        
        try:
            # EPUB files are ZIP archives
            with zipfile.ZipFile(BytesIO(file_bytes)) as zf:
                content_items = self._get_spine_items(zf)
                
                if not content_items:
                    raise ValueError("No readable content found in EPUB")
                
                all_text_parts = []
                
                for item_path in content_items:
                    try:
                        html_bytes = zf.read(item_path)
                    except KeyError:
                        logger.warning(f"Content file not found: {item_path}")
                        continue
                    
                    if not html_bytes:
                        logger.debug(f"Skipping empty content item: {item_path}")
                        continue
                    
                    # Parse HTML/XHTML content
                    text = self._extract_html_text(html_bytes)
                    if text.strip():
                        all_text_parts.append(text.strip())
                
                if not all_text_parts:
                    raise ValueError("No text content extracted from EPUB")
                
                # Join with double newlines to preserve chapter/section breaks
                return "\n\n".join(all_text_parts)
        
        except zipfile.BadZipFile as e:
            raise RuntimeError(f"Invalid EPUB file (not a valid ZIP): {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to extract EPUB: {e}") from e
    
    def _get_spine_items(self, zf: zipfile.ZipFile) -> list[str]:
        """
        Extract content file paths in spine (reading) order.
        
        The EPUB spine defines the linear reading order of the book.
        This is critical for maintaining narrative flow.
        
        Args:
            zf: Open ZipFile object
            
        Returns:
            List of file paths in reading order
        """
        # Step 1: Find the OPF file location from META-INF/container.xml
        try:
            container_xml = zf.read("META-INF/container.xml")
        except KeyError:
            logger.warning("META-INF/container.xml not found, using fallback order")
            return self._fallback_xhtml_order(zf)
        
        try:
            container_root = ElementTree.fromstring(container_xml)
        except ElementTree.ParseError:
            logger.warning("Failed to parse container.xml, using fallback order")
            return self._fallback_xhtml_order(zf)
        
        # Find the rootfile element that points to the OPF
        rootfile_el = container_root.find(f".//{{{_CONTAINER_NS}}}rootfile")
        if rootfile_el is None:
            logger.warning("No rootfile found in container.xml")
            return self._fallback_xhtml_order(zf)
        
        opf_path = rootfile_el.get("full-path", "")
        if not opf_path:
            logger.warning("Empty OPF path in container.xml")
            return self._fallback_xhtml_order(zf)
        
        # Step 2: Parse the OPF file
        try:
            opf_xml = zf.read(opf_path)
        except KeyError:
            logger.warning(f"OPF file not found: {opf_path}")
            return self._fallback_xhtml_order(zf)
        
        try:
            opf_root = ElementTree.fromstring(opf_xml)
        except ElementTree.ParseError:
            logger.warning(f"Failed to parse OPF file: {opf_path}")
            return self._fallback_xhtml_order(zf)
        
        opf_dir = opf_path.rsplit("/", 1)[0] + "/" if "/" in opf_path else ""
        
        manifest = {}
        for item in opf_root.findall(f".//{{{_OPF_NS}}}item"):
            item_id = item.get("id", "")
            href = item.get("href", "")
            media_type = item.get("media-type", "")
            if item_id and href:
                manifest[item_id] = (href, media_type)
        
        spine_items = []
        for itemref in opf_root.findall(f".//{{{_OPF_NS}}}itemref"):
            idref = itemref.get("idref", "")
            if idref not in manifest:
                continue
            
            href, media_type = manifest[idref]
            
            if media_type not in _XHTML_MEDIA_TYPES:
                continue
            
            full_path = opf_dir + href
            spine_items.append(full_path)
        
        return spine_items if spine_items else self._fallback_xhtml_order(zf)
    
    @staticmethod
    def _fallback_xhtml_order(zf: zipfile.ZipFile) -> list[str]:
        """
        Fallback when metadata parsing fails: alphabetical XHTML file order.
        
        Not ideal (loses authorial intent) but better than failing completely.
        
        Args:
            zf: Open ZipFile object
            
        Returns:
            Alphabetically sorted list of XHTML files
        """
        logger.info("Using fallback alphabetical ordering for EPUB content")
        return sorted(
            name for name in zf.namelist()
            if name.lower().endswith((".xhtml", ".html", ".htm"))
            and not name.startswith("META-INF/")
        )
    
    def _extract_html_text(self, html_bytes: bytes) -> str:
        """
        Extract plain text from HTML/XHTML content.
        
        Lazy imports the HTML parser to avoid loading dependencies
        unless EPUB reading is actually needed.
        
        Args:
            html_bytes: Raw HTML/XHTML bytes
            
        Returns:
            Extracted plain text
        """
        try:
            from src.ingestion.utils.html_parser import HTMLParser
        except ImportError as e:
            raise RuntimeError(
                "HTML parser utility not found. Ensure ingestion/utils/html_parser.py exists."
            ) from e
        
        parser = HTMLParser()
        return parser.extract_text(html_bytes)