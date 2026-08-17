import sys
import types

import pytest

from src.ingestion.utils.html_parser import HTMLParser


def test_extract_text_happy_path_with_utf8():
    parser = HTMLParser()

    class FakeSoup:
        def __call__(self, tags):
            return []

        def get_text(self, separator="\n", strip=True):
            return "Title\nBody"

    fake_bs4 = types.SimpleNamespace(BeautifulSoup=lambda *_args, **_kwargs: FakeSoup())

    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "bs4", fake_bs4)
        out = parser.extract_text(b"<html></html>")

    assert out == "Title\n\nBody"


def test_extract_text_with_encoding_hint():
    parser = HTMLParser()

    class FakeSoup:
        def __call__(self, tags):
            return []

        def get_text(self, separator="\n", strip=True):
            return "A"

    fake_bs4 = types.SimpleNamespace(BeautifulSoup=lambda *_args, **_kwargs: FakeSoup())
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "bs4", fake_bs4)
        out = parser.extract_text("<x/>".encode("latin-1"), encoding="latin-1")

    assert out == "A"


def test_extract_text_import_error_for_bs4():
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "bs4", None)
        with pytest.raises(RuntimeError, match="BeautifulSoup4"):
            HTMLParser().extract_text(b"x")


def test_decode_with_detection_fallback_without_chardet():
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "chardet", None)
        out = HTMLParser._decode_with_detection(b"abc")
    assert out == "abc"


def test_decode_with_detection_low_confidence_uses_utf8():
    fake = types.SimpleNamespace(detect=lambda b: {"encoding": "latin-1", "confidence": 0.1})
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "chardet", fake)
        out = HTMLParser._decode_with_detection("hello".encode("utf-8"))
    assert out == "hello"


def test_extract_text_wraps_parser_exceptions():
    class BrokenSoup:
        def __call__(self, tags):
            return []

        def get_text(self, separator="\n", strip=True):
            raise Exception("parse fail")

    fake_bs4 = types.SimpleNamespace(BeautifulSoup=lambda *_args, **_kwargs: BrokenSoup())
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "bs4", fake_bs4)
        with pytest.raises(RuntimeError, match="HTML parsing failed"):
            HTMLParser().extract_text(b"<html></html>")


def test_extract_text_utf8_decode_fallback_to_detection():
    parser = HTMLParser()

    class FakeSoup:
        def __call__(self, tags):
            return []

        def get_text(self, separator="\n", strip=True):
            return "decoded"

    fake_bs4 = types.SimpleNamespace(BeautifulSoup=lambda *_args, **_kwargs: FakeSoup())
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "bs4", fake_bs4)
        mp.setattr(parser, "_decode_with_detection", lambda b: "<html>ok</html>")
        out = parser.extract_text(b"\xff\xfe\x00")

    assert out == "decoded"
