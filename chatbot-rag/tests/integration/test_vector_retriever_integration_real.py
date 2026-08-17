"""
Real integration tests for `src.vector.vector_retriever`.

These tests interact with a running Qdrant instance. They will be skipped
automatically if QDRANT_URL (and optionally QDRANT_PORT) environment variables
are not set. Tests do not mock the vector DB calls; they create a temporary
collection, upsert real points and query it via the same query path used by
the application.

Note: Reranking tests are skipped by default because the reranker can attempt
to load large models. Set environment variable `RUN_RERANKER_INTEGRATION=1`
to enable reranker-related tests (only do this when models are available
and you accept the download/compute cost).
"""
from src.utils.config_loader import get_config
import os
import threading
import time
import uuid
from typing import Any, List

import pytest

from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.models import RetrievalResult
from src.vector import vector_retriever


def _require_env():
    """
    Determine Qdrant connection details. Prefer values from `config.yaml`
    via `get_config`, fall back to environment variables. If no URL is
    available, skip the integration tests.
    """
        

    url = get_config("vector.qdrant_url") 
    port = get_config("vector.qdrant_port") 

    if not url:
        pytest.skip("QDRANT_URL not set in config.yaml; skipping real integration tests")

    return url, int(port) if port else None


class RealQdrantWrapper:
    """A small adapter around QdrantClient that exposes query_collection
    with the same signature as used by VectorRetriever.
    """

    def __init__(self, client: QdrantClient):
        self.client = client

    def query_collection(self, collection_name: str, query_embedding: Any, top_k: int = 30) -> List[RetrievalResult]:
        # qdrant returns PointsSearchResult with .points
        resp = self.client.query_points(collection_name=collection_name, query=query_embedding, limit=top_k, with_payload=True)
        points = getattr(resp, "points", [])
        formatted = []
        for p in points:
            payload = p.payload or {}
            content = payload.get("page_content") or payload.get("content") or ""
            metadata = payload.copy()
            metadata.pop("page_content", None)
            metadata.pop("content", None)
            formatted.append(RetrievalResult(content=content, metadata=metadata, relevance_score=p.score))
        return formatted


class SimpleEmbeddingManager:
    def embed_single_text(self, text: str):
        # return a small fixed-dimension embedding expected by this test
        # use deterministic numeric values derived from text
        return [float(len(text) % 10), float(sum(ord(c) for c in text) % 100) / 100.0, 0.123]


def _create_collection(client: QdrantClient, name: str, vector_size: int = 3):
    try:
        client.delete_collection(collection_name=name)
    except Exception:
        pass
    client.create_collection(collection_name=name, vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE))


def _upsert_points(client: QdrantClient, collection_name: str, points: List[dict]):
    p_structs = [models.PointStruct(id=p["id"], vector=p["vector"], payload=p.get("payload", {})) for p in points]
    client.upsert(collection_name=collection_name, points=p_structs)


@pytest.mark.integration
def test_retrieve_against_real_qdrant():
    """
    Happy path integration test: create a collection, upsert points and verify
    that VectorRetriever.retrieve returns expected documents.

    Assertions:
    - retrieve returns up to top_k results
    - returned items include the content we upserted
    """
    url, port = _require_env()
    api_key = os.getenv("QDRANT_API_KEY")

    client = QdrantClient(url=url, port=port, api_key=api_key)
    wrapper = RealQdrantWrapper(client)

    collection = f"test_vr_{uuid.uuid4().hex[:8]}"
    _create_collection(client, collection, vector_size=3)

    try:
        # prepare points
        docs = [
            {"id": i + 1, "vector": [0.1 * (i + 1), 0.2 * (i + 1), 0.3], "payload": {"content": f"doc-{i}"}} for i in range(5)
        ]
        _upsert_points(client, collection, docs)

        retriever = vector_retriever.VectorRetriever(embedding_manager=SimpleEmbeddingManager())
        # override to use our real client wrapper and the test collection
        retriever.client = wrapper
        retriever.collection_name = collection

        results = retriever.retrieve("integration-query")

        assert isinstance(results, list)
        assert len(results) <= retriever.top_k
        # expected content present
        contents = {r.content for r in results}
        assert any(c.startswith("doc-") for c in contents)
    finally:
        try:
            client.delete_collection(collection_name=collection)
        except Exception:
            pass


@pytest.mark.integration
def test_retrieve_with_reranking_reranker_none_raises(monkeypatch):
    """
    Negative test: when `reranker` is not configured on the `VectorRetriever`,
    calling `retrieve_with_reranking` should raise ValueError as documented.

    This test does not mock external DB or reranker; it uses the real Qdrant
    client (skips if not configured) but removes the reranker attribute to
    trigger the error path.
    """
    url, port = _require_env()
    api_key = os.getenv("QDRANT_API_KEY")

    client = QdrantClient(url=url, port=port, api_key=api_key)

    collection = f"test_vr_{uuid.uuid4().hex[:8]}"
    _create_collection(client, collection, vector_size=3)

    try:
        docs = [
            {"id": 1, "vector": [0.1, 0.2, 0.3], "payload": {"content": "doc-1"}},
        ]
        _upsert_points(client, collection, docs)

        retriever = vector_retriever.VectorRetriever(embedding_manager=SimpleEmbeddingManager())
        retriever.client = RealQdrantWrapper(client)
        retriever.collection_name = collection

        # Remove reranker to test the error path
        retriever.reranker = None

        with pytest.raises(ValueError):
            retriever.retrieve_with_reranking("q", initial_k=2)
    finally:
        try:
            client.delete_collection(collection_name=collection)
        except Exception:
            pass


@pytest.mark.integration
def test_invalid_queries_raise():
    """
    Negative test: verify that passing None or empty string as query raises
    AttributeError for both retrieve and retrieve_with_reranking.
    """
    url, port = _require_env()
    api_key = os.getenv("QDRANT_API_KEY")

    client = QdrantClient(url=url, port=port, api_key=api_key)
    wrapper = RealQdrantWrapper(client)

    collection = f"test_vr_{uuid.uuid4().hex[:8]}"
    _create_collection(client, collection, vector_size=3)

    try:
        retriever = vector_retriever.VectorRetriever(embedding_manager=SimpleEmbeddingManager())
        retriever.client = wrapper
        retriever.collection_name = collection

        with pytest.raises(AttributeError):
            retriever.retrieve(None)

        with pytest.raises(AttributeError):
            retriever.retrieve("")

        with pytest.raises(AttributeError):
            retriever.retrieve_with_reranking(None)

        with pytest.raises(AttributeError):
            retriever.retrieve_with_reranking("")
    finally:
        try:
            client.delete_collection(collection_name=collection)
        except Exception:
            pass


@pytest.mark.integration
def test_concurrent_retrieves_against_real_qdrant():
    """
    Concurrency test: run multiple threads calling retrieve concurrently
    and ensure all threads get results and Qdrant handled concurrent requests.
    """
    url, port = _require_env()
    api_key = os.getenv("QDRANT_API_KEY")

    client = QdrantClient(url=url, port=port, api_key=api_key)
    wrapper = RealQdrantWrapper(client)

    collection = f"test_vr_{uuid.uuid4().hex[:8]}"
    _create_collection(client, collection, vector_size=3)

    try:
        docs = [
            {"id": i + 1, "vector": [0.1 * (i + 1), 0.2 * (i + 1), 0.3], "payload": {"content": f"doc-{i}"}} for i in range(3)
        ]
        _upsert_points(client, collection, docs)

        retriever = vector_retriever.VectorRetriever(embedding_manager=SimpleEmbeddingManager())
        retriever.client = wrapper
        retriever.collection_name = collection

        n_threads = 6
        results = [None] * n_threads

        def worker(idx):
            results[idx] = retriever.retrieve(f"q-{idx}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for r in results:
            assert isinstance(r, list)
    finally:
        try:
            client.delete_collection(collection_name=collection)
        except Exception:
            pass
