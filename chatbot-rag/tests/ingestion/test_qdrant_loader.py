from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.ingestion.qdrant_loader import QdrantLoader, display_search_results, main
from src.models import RetrievalResult


@pytest.fixture
def loader():
    cfg = {
        "vector.collection_name": "test_collection",
        "vector.embedding_model_name": "test-model",
        "ingestion.scroll_batch_size": 2,
    }

    with (
        patch("src.ingestion.qdrant_loader.get_config", side_effect=lambda k, default=None: cfg.get(k, default)),
        patch("src.ingestion.qdrant_loader.TextChunker") as chunker_cls,
        patch("src.ingestion.qdrant_loader.EmbeddingManager") as emb_cls,
        patch("src.ingestion.qdrant_loader.QdrantDBClient") as qd_cls,
        patch("src.ingestion.qdrant_loader.DocumentReader") as reader_cls,
    ):
        chunker = MagicMock()
        chunker.chunk.return_value = [
            {"text": "chunk one", "chunk_id": 0, "metadata": {"chunk_type": "text"}},
            {"text": "chunk two", "chunk_id": 1, "metadata": {"chunk_type": "text"}},
        ]
        chunker_cls.return_value = chunker

        emb = MagicMock()
        emb.embed_texts.return_value = np.array([[0.1, 0.2], [0.2, 0.3]])
        emb.embed_single_text.return_value = np.array([0.4, 0.5])
        emb_cls.return_value = emb

        qd = MagicMock()
        qd.query_collection.return_value = [
            RetrievalResult(content="c1", metadata={"document_name": "a.docx"}, relevance_score=0.9),
            RetrievalResult(content="c2", metadata={"document_name": "b.docx"}, relevance_score=0.6),
        ]
        qd.count.return_value = 7
        qd.client.count.return_value = MagicMock(count=3)
        qd.client.scroll.return_value = ([MagicMock(payload={"document_name": "a.docx", "document_stem": "a"})], None)
        qd_cls.return_value = qd

        reader = MagicMock()
        reader_cls.return_value = reader

        inst = QdrantLoader()
        inst.chunker = chunker
        inst.embedding_manager = emb
        inst.qdrant_db_client = qd
        inst.document_reader = reader
        return inst


def test_init_calls_ensure_collection(loader):
    loader.qdrant_db_client.ensure_collection.assert_called_once_with("test_collection")


def test_read_from_bytes_happy_path(loader):
    loader.document_reader.extract.return_value = "hello"
    out = loader._read_from_bytes(b"x", "f.pdf")
    assert out == "hello"


def test_read_from_bytes_wraps_error(loader):
    loader.document_reader.extract.side_effect = Exception("bad")
    with pytest.raises(RuntimeError, match="Failed to read document"):
        loader._read_from_bytes(b"x", "f.pdf")


def test_process_document_success(loader):
    with patch.object(loader, "_read_from_bytes", return_value="content text"):
        with patch.object(loader, "get_document_chunk_count", return_value=0):
            out = loader.process_document(b"bytes", "my.docx")

    assert out["status"] == "success"
    assert out["was_replaced"] is False
    assert out["chunks_created"] == 2
    loader.qdrant_db_client.upsert.assert_called_once()


def test_process_document_replacement_path(loader):
    with patch.object(loader, "_read_from_bytes", return_value="content text"):
        with patch.object(loader, "get_document_chunk_count", return_value=5):
            with patch.object(loader, "delete_document_chunks") as d:
                out = loader.process_document(b"bytes", "my.docx")

    d.assert_called_once_with("my.docx")
    assert out["was_replaced"] is True
    assert out["old_chunk_count"] == 5


def test_process_document_error_path_returns_error_dict(loader):
    with patch.object(loader, "_read_from_bytes", side_effect=Exception("boom")):
        out = loader.process_document(b"bytes", "my.docx")
    assert out["status"] == "error"
    assert "boom" in out["error"]


def test_search_happy_path_and_metadata_flag(loader):
    out = loader.search("q", top_k=2, include_metadata=False)
    assert out[0]["rank"] == 1
    assert out[0]["metadata"] is None
    loader.qdrant_db_client.query_collection.assert_called_once()


def test_search_re_raises_exception(loader):
    loader.qdrant_db_client.query_collection.side_effect = Exception("query failed")
    with pytest.raises(Exception, match="query failed"):
        loader.search("q")


def test_get_collection_stats(loader):
    out = loader.get_collection_stats()
    assert out["collection_name"] == "test_collection"
    assert out["total_documents"] == 7


def test_delete_document_chunks(loader):
    out = loader.delete_document_chunks("a.docx")
    assert out == 0
    loader.qdrant_db_client.delete_by_filter.assert_called_once_with("test_collection", "document_name", "a.docx")


def test_scroll_all_points_multi_page(loader):
    loader.qdrant_db_client.client.scroll.side_effect = [
        ([MagicMock(payload={"document_name": "a.docx", "document_stem": "a"})], "off1"),
        ([MagicMock(payload={"document_name": "b.docx", "document_stem": "b"})], None),
    ]
    pts = list(loader._scroll_all_points())
    assert len(pts) == 2


def test_unique_document_count_and_list_documents(loader):
    loader.qdrant_db_client.client.scroll.return_value = (
        [
            MagicMock(payload={"document_name": "a.docx", "document_stem": "a"}),
            MagicMock(payload={"document_name": "a.docx", "document_stem": "a"}),
            MagicMock(payload={"document_name": "b.docx", "document_stem": "b"}),
            MagicMock(payload=None),
        ],
        None,
    )
    assert loader.get_unique_document_count() == 2
    docs = loader.list_documents()
    assert len(docs) == 2
    a = next(d for d in docs if d["document_name"] == "a.docx")
    assert a["chunk_count"] == 2


def test_get_document_chunk_count_success_and_error(loader):
    assert loader.get_document_chunk_count("a.docx") == 3
    loader.qdrant_db_client.client.count.side_effect = Exception("x")
    assert loader.get_document_chunk_count("a.docx") == 0


def test_display_search_results_empty_and_non_empty(capsys):
    display_search_results([], "q")
    out1 = capsys.readouterr().out
    assert "No results found" in out1

    display_search_results(
        [{"content": "hello world", "relevance_score": 0.8, "metadata": {"document_name": "d.docx"}}],
        "q2",
    )
    out2 = capsys.readouterr().out
    assert "SUMMARY" in out2
    assert "hello world" in out2


def test_main_stats_and_list_docs_paths():
    fake = MagicMock()
    fake.get_collection_stats.return_value = {
        "collection_name": "c",
        "total_documents": 1,
        "embedding_model": "m",
        "provider": "p",
    }
    fake.list_documents.return_value = [{"document_name": "a.docx", "chunk_count": 2}]

    with patch("src.ingestion.qdrant_loader.QdrantLoader", return_value=fake):
        with patch("sys.argv", ["qdrant_loader.py", "--stats", "--list-docs"]):
            main()


def test_main_exits_when_no_args():
    with patch("sys.argv", ["qdrant_loader.py"]):
        with pytest.raises(SystemExit):
            main()
