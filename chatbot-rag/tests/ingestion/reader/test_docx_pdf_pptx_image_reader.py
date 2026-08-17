import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.reader.docx_reader import DOCXReader, DOCReader
from src.ingestion.reader.pdf_reader import PDFReader
from src.ingestion.reader.pptx_reader import PPTXReader, PPTReader
from src.ingestion.reader.image_reader import ImageReader


def test_docx_reader_extract_happy_path_without_ocr_module():
    fake_docx = types.SimpleNamespace(
        paragraphs=[types.SimpleNamespace(text="Para 1")],
        tables=[],
    )
    fake_doc_ctor = MagicMock(return_value=fake_docx)

    with patch.dict(sys.modules, {"docx": types.SimpleNamespace(Document=fake_doc_ctor)}):
        with patch.object(DOCXReader, "_extract_images", return_value=[]):
            out = DOCXReader().extract(b"bytes")

    assert "Para 1" in out


def test_docx_reader_empty_bytes_raises():
    with pytest.raises(ValueError, match="Empty Word"):
        DOCXReader().extract(b"")


def test_docx_reader_extract_wraps_errors():
    with patch.dict(sys.modules, {"docx": types.SimpleNamespace(Document=MagicMock(side_effect=Exception("bad")))}):
        with pytest.raises(RuntimeError, match="Failed to read Word"):
            DOCXReader().extract(b"x")


def test_docx_reader_extract_table_variants():
    reader = DOCXReader()
    t1 = types.SimpleNamespace(rows=[types.SimpleNamespace(cells=[types.SimpleNamespace(text="A"), types.SimpleNamespace(text="B")])])
    assert reader._extract_table(t1) == "A | B"

    t2 = types.SimpleNamespace(
        rows=[
            types.SimpleNamespace(cells=[types.SimpleNamespace(text="H1"), types.SimpleNamespace(text="H2")]),
            types.SimpleNamespace(cells=[types.SimpleNamespace(text="V1"), types.SimpleNamespace(text="")]),
        ]
    )
    assert "H1: V1" in reader._extract_table(t2)


def test_doc_reader_legacy_raises_runtime_error():
    with pytest.raises(RuntimeError, match="Legacy .doc"):
        DOCReader().extract(b"x")


def test_docx_reader_import_error_path():
    with patch.dict(sys.modules, {"docx": None}):
        with pytest.raises(RuntimeError, match="python-docx is required"):
            DOCXReader().extract(b"x")


def test_docx_reader_extract_images_path():
    rel1 = types.SimpleNamespace(target_ref="media/image1.png", target_part=types.SimpleNamespace(blob=b"img1"))
    rel2 = types.SimpleNamespace(target_ref="styles.xml", target_part=types.SimpleNamespace(blob=b"skip"))
    fake_doc = types.SimpleNamespace(part=types.SimpleNamespace(rels={"a": rel1, "b": rel2}))
    doc_ctor = MagicMock(return_value=fake_doc)
    imgs = DOCXReader()._extract_images(b"x", doc_ctor)
    assert imgs == [b"img1"]


def test_docx_reader_extract_with_ocr_results_appended():
    fake_docx = types.SimpleNamespace(paragraphs=[types.SimpleNamespace(text="P")], tables=[])
    fake_doc_ctor = MagicMock(return_value=fake_docx)
    fake_ocr_mod = types.SimpleNamespace(run_ocr=lambda b: "OCR-TEXT")
    with patch.dict(sys.modules, {"docx": types.SimpleNamespace(Document=fake_doc_ctor), "src.ingestion.utils.ocr": fake_ocr_mod}):
        with patch.object(DOCXReader, "_extract_images", return_value=[b"img"]):
            out = DOCXReader().extract(b"bytes")
    assert "[Image OCR]" in out
    assert "OCR-TEXT" in out


def test_pdf_reader_extract_happy_path_without_ocr():
    fake_page = types.SimpleNamespace(extract_text=lambda: "This is valid text more than fifty chars long so no ocr path triggered.")
    fake_pdf = types.SimpleNamespace(pages=[fake_page])

    class FakeCtx:
        def __enter__(self):
            return fake_pdf

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_pdfplumber = types.SimpleNamespace(open=lambda _: FakeCtx())
    with patch.dict(sys.modules, {"pdfplumber": fake_pdfplumber}):
        out = PDFReader().extract(b"pdf")

    assert "valid text" in out


def test_pdf_reader_empty_bytes_raises():
    with pytest.raises(ValueError, match="Empty PDF"):
        PDFReader().extract(b"")


def test_pdf_reader_no_text_raises_value_error():
    fake_page = types.SimpleNamespace(extract_text=lambda: "")
    fake_pdf = types.SimpleNamespace(pages=[fake_page])

    class FakeCtx:
        def __enter__(self):
            return fake_pdf

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_pdfplumber = types.SimpleNamespace(open=lambda _: FakeCtx())
    reader = PDFReader()
    with patch.dict(sys.modules, {"pdfplumber": fake_pdfplumber}):
        with patch.object(reader, "_fallback_ocr", return_value=("", None)):
            with pytest.raises(ValueError, match="No text could be extracted"):
                reader.extract(b"pdf")


def test_pdf_reader_is_garbled_cid_and_clean_paths():
    r = PDFReader()
    assert r._is_garbled("(cid:123)") is True
    assert r._is_garbled("normal readable text") is False


def test_pdf_reader_is_garbled_pua_ratio_path():
    r = PDFReader()
    garbled = "\ue000\ue001\ue002 a"
    assert r._is_garbled(garbled) is True


def test_pdf_reader_extract_with_pdfplumber_ocr_branch():
    fake_page = types.SimpleNamespace(extract_text=lambda: "short")
    fake_pdf = types.SimpleNamespace(pages=[fake_page])

    class FakeCtx:
        def __enter__(self):
            return fake_pdf

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_pdfplumber = types.SimpleNamespace(open=lambda *_args, **_kwargs: FakeCtx())
    r = PDFReader()
    with patch.dict(sys.modules, {"pdfplumber": fake_pdfplumber}):
        with patch.object(r, "_fallback_ocr", return_value=("ocr text", None)):
            pages = r._extract_with_pdfplumber(b"x")
    assert pages == ["ocr text"]


def test_pptx_reader_extract_happy_path():
    fake_shape = types.SimpleNamespace(text="Slide text")
    fake_slide = types.SimpleNamespace(shapes=[fake_shape], has_notes_slide=False)
    fake_prs = types.SimpleNamespace(slides=[fake_slide])

    with patch.dict(sys.modules, {"pptx": types.SimpleNamespace(Presentation=MagicMock(return_value=fake_prs))}):
        with patch.object(PPTXReader, "_extract_images", return_value=[]):
            out = PPTXReader().extract(b"pptx")

    assert "Slide 1" in out
    assert "Slide text" in out


def test_pptx_reader_extract_slide_with_notes_and_table():
    table = types.SimpleNamespace(
        rows=[types.SimpleNamespace(cells=[types.SimpleNamespace(text="H"), types.SimpleNamespace(text="V")])]
    )
    shape_text = types.SimpleNamespace(text="Main")
    shape_table = types.SimpleNamespace(text="", table=table)
    notes_slide = types.SimpleNamespace(notes_text_frame=types.SimpleNamespace(text="Speaker note"))
    slide = types.SimpleNamespace(shapes=[shape_text, shape_table], has_notes_slide=True, notes_slide=notes_slide)

    out = PPTXReader()._extract_slide(slide, 2)
    assert "Slide 2" in out
    assert "Main" in out
    assert "H | V" in out
    assert "Notes" in out


def test_pptx_reader_empty_and_legacy_paths():
    with pytest.raises(ValueError, match="Empty PowerPoint"):
        PPTXReader().extract(b"")
    with pytest.raises(RuntimeError, match="Legacy .ppt"):
        PPTReader().extract(b"x")


def test_pptx_reader_import_error_path():
    with patch.dict(sys.modules, {"pptx": None}):
        with pytest.raises(RuntimeError, match="python-pptx"):
            PPTXReader().extract(b"x")


def test_pptx_reader_empty_slide_still_returns_slide_marker():
    fake_slide = types.SimpleNamespace(shapes=[], has_notes_slide=False)
    fake_prs = types.SimpleNamespace(slides=[fake_slide])
    with patch.dict(sys.modules, {"pptx": types.SimpleNamespace(Presentation=MagicMock(return_value=fake_prs))}):
        with patch.object(PPTXReader, "_extract_images", return_value=[]):
            out = PPTXReader().extract(b"x")
    assert "Slide 1" in out


def test_pptx_extract_images_shape_types():
    img_shape = types.SimpleNamespace(shape_type=13, image=types.SimpleNamespace(blob=b"img"))
    other_shape = types.SimpleNamespace(shape_type=1)
    slide = types.SimpleNamespace(shapes=[img_shape, other_shape])
    prs = types.SimpleNamespace(slides=[slide])
    p_ctor = MagicMock(return_value=prs)
    out = PPTXReader()._extract_images(b"x", p_ctor)
    assert out == [b"img"]


def test_image_reader_extract_happy_path():
    fake_engine = MagicMock()
    fake_engine.extract_text.return_value = "ocr text"

    fake_module = types.SimpleNamespace(get_ocr_engine=MagicMock(return_value=fake_engine))
    with patch.dict(sys.modules, {"src.ingestion.utils.ocr": fake_module}):
        out = ImageReader().extract(b"img")

    assert out == "ocr text"


def test_image_reader_empty_or_blank_or_import_error_paths():
    with pytest.raises(ValueError, match="Empty image"):
        ImageReader().extract(b"")

    fake_engine = MagicMock()
    fake_engine.extract_text.return_value = "   "
    fake_module = types.SimpleNamespace(get_ocr_engine=MagicMock(return_value=fake_engine))
    with patch.dict(sys.modules, {"src.ingestion.utils.ocr": fake_module}):
        with pytest.raises(RuntimeError, match="Failed to extract text"):
            ImageReader().extract(b"x")

    with patch.dict(sys.modules, {"src.ingestion.utils.ocr": None}):
        with pytest.raises(RuntimeError, match="OCR utility not found"):
            ImageReader().extract(b"x")


def test_image_reader_engine_exception_wrapped():
    fake_engine = MagicMock()
    fake_engine.extract_text.side_effect = Exception("ocr crash")
    fake_module = types.SimpleNamespace(get_ocr_engine=MagicMock(return_value=fake_engine))
    with patch.dict(sys.modules, {"src.ingestion.utils.ocr": fake_module}):
        with pytest.raises(RuntimeError, match="Failed to extract text"):
            ImageReader().extract(b"img")
