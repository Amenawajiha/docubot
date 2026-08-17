import sys
import types
from unittest.mock import patch

import pytest

from src.ingestion.reader.txt_reader import TextReader
from src.ingestion.reader.md_reader import MarkdownReader


def test_text_reader_extract_happy_path_utf8():
    r = TextReader()
    with patch.object(TextReader, "_detect_encoding", return_value="utf-8"):
        out = r.extract("hello".encode("utf-8"))
    assert out == "hello"


def test_text_reader_empty_bytes_raises():
    with pytest.raises(ValueError, match="Empty TXT"):
        TextReader().extract(b"")


def test_text_reader_fallback_to_latin1_on_decode_error():
    r = TextReader()
    with patch.object(TextReader, "_detect_encoding", return_value="fake-enc"):
        out = r.extract(b"abc")
    assert out == "abc"


def test_text_reader_raises_when_only_whitespace():
    r = TextReader()
    with patch.object(TextReader, "_detect_encoding", return_value="utf-8"):
        with pytest.raises(ValueError, match="TXT file is empty"):
            r.extract(b"   \n\t ")


def test_detect_encoding_with_low_confidence_defaults_utf8():
    fake_chardet = types.SimpleNamespace(detect=lambda b: {"encoding": "ascii", "confidence": 0.1})
    with patch.dict(sys.modules, {"chardet": fake_chardet}):
        assert TextReader._detect_encoding(b"a") == "utf-8"


def test_detect_encoding_without_chardet_defaults_utf8():
    with patch.dict(sys.modules, {"chardet": None}):
        assert TextReader._detect_encoding(b"a") == "utf-8"


def test_markdown_reader_extract_happy_path_with_table_and_syntax():
    md = b"# Title\n\n| Col1 | Col2 |\n| --- | --- |\n| A | B |\n\nText with [link](http://x)."
    out = MarkdownReader().extract(md)
    assert "Title" in out
    assert "Col1: A" in out
    assert "Text with link" in out


def test_markdown_reader_empty_raises():
    with pytest.raises(ValueError, match="No content found"):
        MarkdownReader().extract(b"")


def test_markdown_reader_no_content_after_strip_raises():
    content = b"```code```\n\n![img](x.png)"
    with pytest.raises(ValueError, match="No text content"):
        MarkdownReader().extract(content)
