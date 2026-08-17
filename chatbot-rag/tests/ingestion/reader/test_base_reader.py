import pytest

from src.ingestion.reader.base_reader import BaseReader


class GoodReader(BaseReader):
    @property
    def supported_extensions(self) -> list[str]:
        return [".x"]

    def extract(self, file_bytes: bytes) -> str:
        return "ok"


def test_base_reader_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseReader()


def test_concrete_subclass_implements_contract():
    r = GoodReader()
    assert r.extract(b"x") == "ok"
    assert r.supported_extensions == [".x"]
