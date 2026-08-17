from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
from dataclasses import dataclass


@dataclass
class LoadedDocument:
    """Represents a loaded document"""

    content: str
    metadata: dict
    source_file: str
    file_type: str
    chunk_id: int
    total_chunks: int


@dataclass
class Chunk:
    """Represents a text chunk"""

    text: str
    chunk_id: int
    start_char: int
    end_char: int
    metadata: dict
