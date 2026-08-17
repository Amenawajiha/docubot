import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.reader.epub_reader import EPUBReader
from src.ingestion.reader.xlsx_reader import XLSXReader, CSVReader


def test_epub_reader_empty_raises():
    with pytest.raises(ValueError, match="Empty EPUB"):
        EPUBReader().extract(b"")


def test_epub_reader_invalid_zip_raises_runtime_error():
    with pytest.raises(RuntimeError, match="Invalid EPUB file"):
        EPUBReader().extract(b"not-a-zip")


def test_epub_reader_happy_path_fallback_order_and_html_parse():
    # Fake zipfile with minimal behavior
    class FakeZip:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, name):
            if name == "META-INF/container.xml":
                raise KeyError()
            return b"<html><body>Hello chapter</body></html>"

        def namelist(self):
            return ["a.xhtml"]

    fake_html_parser = types.SimpleNamespace(HTMLParser=lambda: types.SimpleNamespace(extract_text=lambda b: "Hello chapter"))
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "src.ingestion.utils.html_parser", fake_html_parser)
        mp.setattr("zipfile.ZipFile", lambda *_args, **_kwargs: FakeZip())
        out = EPUBReader().extract(b"zip-bytes")

    assert "Hello chapter" in out


def test_xlsx_reader_empty_raises():
    with pytest.raises(ValueError, match="Empty spreadsheet"):
        XLSXReader().extract(b"")


def test_xlsx_reader_extract_happy_path_via_mock_workbook():
    r = XLSXReader()

    class Sheet:
        def iter_rows(self, values_only=True):
            return iter([
                ["Name", "Age"],
                ["Alice", 30],
            ])

    class WB:
        sheetnames = ["Data"]

        def __getitem__(self, key):
            return Sheet()

        def close(self):
            return None

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(r, "_load_workbook", lambda _b: WB())
        out = r.extract(b"bytes")

    assert "Name is Alice" in out
    assert "Age is 30" in out


def test_xlsx_reader_workbook_to_text_no_data_raises():
    r = XLSXReader()

    class EmptySheet:
        def iter_rows(self, values_only=True):
            return iter([])

    class WB:
        sheetnames = ["S1"]

        def __getitem__(self, key):
            return EmptySheet()

    with pytest.raises(ValueError, match="No valid data"):
        r._workbook_to_text(WB())


def test_csv_reader_supported_extensions():
    assert CSVReader().supported_extensions == [".csv"]


def test_epub_get_spine_items_valid_opf_path():
    container = b'''<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>'''
    opf = b'''<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c1"/></spine></package>'''

    class FakeZip:
        def read(self, name):
            if name == "META-INF/container.xml":
                return container
            if name == "OEBPS/content.opf":
                return opf
            raise KeyError(name)

        def namelist(self):
            return ["OEBPS/c1.xhtml"]

    items = EPUBReader()._get_spine_items(FakeZip())
    assert items == ["OEBPS/c1.xhtml"]


def test_epub_fallback_xhtml_order_filters_meta_inf():
    class FakeZip:
        def namelist(self):
            return ["META-INF/a.xhtml", "b.xhtml", "a.html", "c.txt"]

    out = EPUBReader._fallback_xhtml_order(FakeZip())
    assert out == ["a.html", "b.xhtml"]


def test_epub_extract_html_text_import_error():
    with patch.dict(sys.modules, {"src.ingestion.utils.html_parser": None}):
        with pytest.raises(RuntimeError, match="HTML parser utility not found"):
            EPUBReader()._extract_html_text(b"<html></html>")


def test_xlsx_clean_and_csv_load_branch():
    reader = XLSXReader()
    assert reader._clean("a\x01b") == "a b"

    class FakeDF:
        columns = ["A"]

        class _Vals:
            def tolist(self):
                return [["v1"]]

        values = _Vals()

    fake_pd = types.SimpleNamespace(
        DataFrame=FakeDF,
        read_csv=lambda *_args, **_kwargs: FakeDF(),
        read_excel=lambda *_args, **_kwargs: {"Sheet1": FakeDF()},
    )
    fake_openpyxl = types.SimpleNamespace(load_workbook=lambda *_args, **_kwargs: (_ for _ in ()).throw(Exception("xlsx fail")))

    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "pandas", fake_pd)
        mp.setitem(sys.modules, "openpyxl", fake_openpyxl)
        wb = reader._load_workbook(b"notexcel")
    assert wb.sheetnames == ["Sheet1"]


def test_xlsx_load_workbook_raises_when_all_strategies_fail():
    reader = XLSXReader()

    class FakeDF:
        pass

    fake_pd = types.SimpleNamespace(
        DataFrame=FakeDF,
        read_csv=lambda *_args, **_kwargs: (_ for _ in ()).throw(Exception("csv fail")),
        read_excel=lambda *_args, **_kwargs: (_ for _ in ()).throw(Exception("excel fail")),
    )
    fake_openpyxl = types.SimpleNamespace(load_workbook=lambda *_args, **_kwargs: (_ for _ in ()).throw(Exception("xlsx fail")))

    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "pandas", fake_pd)
        mp.setitem(sys.modules, "openpyxl", fake_openpyxl)
        with pytest.raises(RuntimeError, match="Could not load spreadsheet"):
            reader._load_workbook(b"PK\x03\x04xxx")


def test_epub_get_spine_items_missing_container_falls_back():
    class FakeZip:
        def read(self, name):
            raise KeyError(name)

        def namelist(self):
            return ["x.xhtml"]

    out = EPUBReader()._get_spine_items(FakeZip())
    assert out == ["x.xhtml"]


def test_epub_get_spine_items_bad_xml_falls_back():
    class FakeZip:
        def read(self, name):
            if name == "META-INF/container.xml":
                return b"<bad"
            raise KeyError(name)

        def namelist(self):
            return ["x.xhtml"]

    out = EPUBReader()._get_spine_items(FakeZip())
    assert out == ["x.xhtml"]


def test_epub_extract_no_content_items_raises_value_error_wrapped():
    class FakeZip:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, name):
            raise KeyError(name)

        def namelist(self):
            return []

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("zipfile.ZipFile", lambda *_args, **_kwargs: FakeZip())
        with pytest.raises(RuntimeError, match="Failed to extract EPUB"):
            EPUBReader().extract(b"zip")


def test_xlsx_extract_runtime_error_path():
    r = XLSXReader()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(r, "_load_workbook", lambda _b: (_ for _ in ()).throw(Exception("load fail")))
        with pytest.raises(RuntimeError, match="Failed to read spreadsheet"):
            r.extract(b"x")


def test_xlsx_df_to_workbook_and_iter_rows():
    r = XLSXReader()

    class FakeDF:
        columns = ["C1", "C2"]

        class _Vals:
            def tolist(self):
                return [["a", "b"]]

        values = _Vals()

    fake_pd = types.SimpleNamespace(DataFrame=FakeDF)
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "pandas", fake_pd)
        wb = r._df_to_workbook(FakeDF())

    sheet = wb["Sheet1"]
    rows = list(sheet.iter_rows(values_only=True))
    assert rows[0] == ["C1", "C2"]
    assert rows[1] == ["a", "b"]
