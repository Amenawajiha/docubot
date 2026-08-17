import sys
import types
from unittest.mock import MagicMock

import pytest

import src.ingestion.utils.ocr as ocr
from src.ingestion.utils.ocr import OCREngine, get_ocr_engine, run_ocr


def test_get_ocr_engine_singleton_cache():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ocr, "_ocr_engines", {})
        mp.setattr(OCREngine, "_initialize_reader", lambda self: object())
        e1 = get_ocr_engine(languages=["en"], gpu=False)
        e2 = get_ocr_engine(languages=["en"], gpu=False)
        e3 = get_ocr_engine(languages=["fr"], gpu=True)
    assert e1 is e2
    assert e1 is not e3


def test_run_ocr_calls_shared_engine():
    fake_engine = MagicMock()
    fake_engine.extract_text.return_value = "text"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ocr, "get_ocr_engine", lambda: fake_engine)
        out = run_ocr(b"img")
    assert out == "text"


def test_extract_text_happy_path_without_preprocessing():
    engine = OCREngine()
    engine._reader = MagicMock(readtext=MagicMock(return_value=[(None, "line1", 0.9), (None, "line2", 0.8)]))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(engine, "_load_image", lambda b: "image")
        out = engine.extract_text(b"img", preprocessing=False)
    assert out == "line1\nline2"


def test_extract_text_no_text_returns_empty_string():
    engine = OCREngine()
    engine._reader = MagicMock(readtext=MagicMock(return_value=[]))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(engine, "_load_image", lambda b: "image")
        out = engine.extract_text(b"img", preprocessing=False)
    assert out == ""


def test_extract_text_wraps_failure_runtime_error():
    engine = OCREngine()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(engine, "_initialize_reader", lambda: (_ for _ in ()).throw(RuntimeError("init fail")))
        with pytest.raises(RuntimeError, match="init fail"):
            engine.extract_text(b"img")


def test_initialize_reader_import_error_path():
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "easyocr", None)
        with pytest.raises(RuntimeError, match="EasyOCR"):
            OCREngine()._initialize_reader()


def test_preprocess_image_when_pil_missing_returns_original():
    arr = [[1, 2], [3, 4]]
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "PIL", None)
        out = OCREngine._preprocess_image(arr)
    assert out == arr


def test_load_image_import_error_path():
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "PIL", None)
        with pytest.raises(RuntimeError, match="PIL and NumPy"):
            OCREngine._load_image(b"img")


def test_initialize_reader_success_path():
    fake_reader_instance = object()
    fake_easyocr = types.SimpleNamespace(Reader=lambda *args, **kwargs: fake_reader_instance)
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "easyocr", fake_easyocr)
        out = OCREngine(languages=["en"], gpu=False)._initialize_reader()
    assert out is fake_reader_instance


def test_initialize_reader_wraps_constructor_errors():
    fake_easyocr = types.SimpleNamespace(Reader=lambda *args, **kwargs: (_ for _ in ()).throw(Exception("ctor fail")))
    with pytest.MonkeyPatch.context() as mp:
        mp.setitem(sys.modules, "easyocr", fake_easyocr)
        with pytest.raises(RuntimeError, match="Failed to initialize EasyOCR"):
            OCREngine()._initialize_reader()
