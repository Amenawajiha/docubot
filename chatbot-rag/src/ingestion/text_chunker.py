"""Lightweight text chunker for document ingestion."""

from typing import List, Dict, Any
from src.utils.config_loader import get_config
from src.utils.log_helper import logger


class TextChunker:
    """Chunks text into manageable pieces for embedding."""

    def __init__(self, preserve_paragraphs: bool = True):
        self.chunk_size = get_config("vector.chunk_size") or 800
        self.chunk_overlap = get_config("vector.chunk_overlap") or 50
        self.min_words = get_config("vector.min_words_per_chunk") or 30
        self.preserve_paragraphs = preserve_paragraphs

        logger.info(
            "TextChunker: chunk_size=%s, chunk_overlap=%s, min_words=%s",
            self.chunk_size,
            self.chunk_overlap,
            self.min_words,
        )

    def _count_words(self, text: str) -> int:
        return len(text.split())

    def chunk(self, text: str, metadata: dict = None) -> List[Dict[str, Any]]:
        """
        Chunk text into overlapping chunks.

        Returns list of dicts with keys: text, chunk_id, start_char, end_char, metadata
        """
        if metadata is None:
            metadata = {}

        logger.info("Starting chunking: %d chars", len(text))

        chunks = []
        chunk_id = 0

        if self.preserve_paragraphs:
            paragraphs = text.split("\n\n")

            buffer_texts = []
            buffer_word_count = 0

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                para_word_count = self._count_words(para)

                # Long paragraph → flush buffer, then split normally
                if len(para) > self.chunk_size:
                    if buffer_texts:
                        combined = "\n\n".join(buffer_texts)
                        chunks.append(
                            {
                                "text": combined,
                                "chunk_id": chunk_id,
                                "start_char": 0,
                                "end_char": len(combined),
                                "metadata": {
                                    **metadata,
                                    "chunk_type": "buffered",
                                    "word_count": buffer_word_count,
                                },
                            }
                        )
                        chunk_id += 1
                        buffer_texts = []
                        buffer_word_count = 0

                    para_chunks = self._chunk_text(para, chunk_id)
                    for pc in para_chunks:
                        pc["metadata"] = {
                            **metadata,
                            **pc.get("metadata", {}),
                            "word_count": self._count_words(pc["text"]),
                        }
                        pc["chunk_id"] = chunk_id
                        chunks.append(pc)
                        chunk_id += 1
                    continue

                # Would exceed chunk size → emit buffer early
                estimated_size = sum(len(p) for p in buffer_texts) + len(para)
                if buffer_texts and estimated_size > self.chunk_size:
                    combined = "\n\n".join(buffer_texts)
                    chunks.append(
                        {
                            "text": combined,
                            "chunk_id": chunk_id,
                            "start_char": 0,
                            "end_char": len(combined),
                            "metadata": {
                                **metadata,
                                "chunk_type": "buffered",
                                "word_count": buffer_word_count,
                            },
                        }
                    )
                    chunk_id += 1
                    buffer_texts = []
                    buffer_word_count = 0

                # Add paragraph to buffer
                buffer_texts.append(para)
                buffer_word_count += para_word_count

                # Buffer reached minimum useful size → emit
                if buffer_word_count >= self.min_words:
                    combined = "\n\n".join(buffer_texts)
                    chunks.append(
                        {
                            "text": combined,
                            "chunk_id": chunk_id,
                            "start_char": 0,
                            "end_char": len(combined),
                            "metadata": {
                                **metadata,
                                "chunk_type": "buffered",
                                "word_count": buffer_word_count,
                            },
                        }
                    )
                    chunk_id += 1
                    buffer_texts = []
                    buffer_word_count = 0

            # Flush remaining buffer
            if buffer_texts:
                combined = "\n\n".join(buffer_texts)
                chunks.append(
                    {
                        "text": combined,
                        "chunk_id": chunk_id,
                        "start_char": 0,
                        "end_char": len(combined),
                        "metadata": {
                            **metadata,
                            "chunk_type": "buffered",
                            "word_count": buffer_word_count,
                        },
                    }
                )
        else:
            chunks = self._chunk_text(text, 0)
            for i, c in enumerate(chunks):
                c["chunk_id"] = i
                c["metadata"] = {
                    **metadata,
                    **c.get("metadata", {}),
                    "word_count": self._count_words(c["text"]),
                }

        logger.info("Chunking complete: %d chunks created", len(chunks))
        return chunks

    def _chunk_text(self, text: str, start_id: int = 0) -> List[Dict[str, Any]]:
        """Simple fixed-size text chunking."""
        chunks: List[Dict[str, Any]] = []
        start_pos = 0
        text_len = len(text)
        chunk_id = start_id

        while start_pos < text_len:
            end_pos = min(start_pos + self.chunk_size, text_len)

            # Try to break at word boundary
            if end_pos < text_len:
                space_pos = text.rfind(" ", start_pos, end_pos)
                if space_pos > start_pos:
                    end_pos = space_pos

            chunk_text = text[start_pos:end_pos].strip()

            if chunk_text:
                chunks.append(
                    {
                        "text": chunk_text,
                        "chunk_id": chunk_id,
                        "start_char": start_pos,
                        "end_char": end_pos,
                        "metadata": {
                            "chunk_type": "fixed_size",
                            "word_count": self._count_words(chunk_text),
                        },
                    }
                )
                chunk_id += 1

            # Move forward with overlap
            next_start = end_pos - self.chunk_overlap

            # Ensure forward progress
            if next_start <= start_pos:
                next_start = start_pos + 1

            start_pos = next_start

        return chunks

    def get_stats(self, chunks: List[Dict[str, Any]]) -> dict:
        """Get statistics about chunks."""
        if not chunks:
            return {"total_chunks": 0}

        sizes = [len(c["text"]) for c in chunks]
        return {
            "total_chunks": len(chunks),
            "total_characters": sum(sizes),
            "avg_chunk_size": sum(sizes) / len(sizes),
            "min_chunk_size": min(sizes),
            "max_chunk_size": max(sizes),
        }
