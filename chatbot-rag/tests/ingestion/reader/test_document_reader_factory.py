import types
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.reader.base import DocumentReader


class DummyReader:
    def extract(self, file_bytes: bytes) -> str:
        return "ok"


def test_extract_happy_path_uses_reader():
    reader = DocumentReader()
    mocked = MagicMock()
    mocked.extract.return_value = "hello"

    with patch.object(reader, "_get_reader", return_value=mocked):
        out = reader.extract(b"abc", "file.txt")

    assert out == "hello"
    mocked.extract.assert_called_once_with(b"abc")


def test_extract_empty_bytes_raises_value_error():
    reader = DocumentReader()
    with pytest.raises(ValueError, match="Empty file provided"):
        reader.extract(b"", "a.pdf")


def test_supported_extensions_sorted():
    reader = DocumentReader()
    exts = reader.supported_extensions
    assert exts == sorted(exts)
    assert ".pdf" in exts


def test_get_reader_unsupported_extension_raises():
    reader = DocumentReader()
    with pytest.raises(ValueError, match="Unsupported file extension"):
        reader._get_reader("x.unsupported")


def test_get_reader_uses_cache_on_second_call():
    reader = DocumentReader()
    reader._reader_cache[".txt"] = DummyReader()
    out = reader._get_reader("a.txt")
    assert isinstance(out, DummyReader)


def test_get_reader_imports_and_caches_instance():
    reader = DocumentReader()
    with patch.object(reader, "_import_reader_class", return_value=DummyReader) as m:
        inst = reader._get_reader("a.txt")
    assert isinstance(inst, DummyReader)
    assert ".txt" in reader._reader_cache
    m.assert_called_once()


def test_import_reader_class_happy_path():
    fake_module = types.SimpleNamespace(PDFReader=DummyReader)
    with patch("importlib.import_module", return_value=fake_module):
        cls = DocumentReader._import_reader_class("pdf_reader", "PDFReader")
    assert cls is DummyReader


@pytest.mark.parametrize("exc", [ImportError("x"), AttributeError("x")])
def test_import_reader_class_raises_import_error(exc):
    with patch("importlib.import_module", side_effect=exc):
        with pytest.raises(ImportError, match="Failed to import"):
            DocumentReader._import_reader_class("missing", "Missing")
