"""
Comprehensive unit tests for DocumentProcessor.

This test suite covers:
- Initialization and configuration
- Document reading (DOCX files)
- Document processing workflow
- Chunking integration
- Embedding generation
- ChromaDB storage
- Search functionality
- Collection management
- Error handling and edge cases
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open, call
import pytest
import numpy as np


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_config():
    """Mock configuration values."""
    config_values = {
        "vector.chroma_db_path": "./test_chroma_db",
        "vector.collection_name": "test_collection",
        "vector.embedding_model_name": "test-model",
        "vector.chunk_size": 800,
        "vector.chunk_overlap": 50,
        "vector.min_words_per_chunk": 30,
        "vector.embedding_batch_size": 2,
    }
    
    def get_config_side_effect(key):
        return config_values.get(key)
    
    with patch("src.ingestion.document_processor.get_config") as mock:
        mock.side_effect = get_config_side_effect
        yield mock


@pytest.fixture
def mock_logger():
    """Mock logger to avoid actual logging during tests."""
    with patch("src.ingestion.document_processor.logger") as mock:
        yield mock


@pytest.fixture
def mock_text_chunker():
    """Mock TextChunker."""
    with patch("src.ingestion.document_processor.TextChunker") as mock_class:
        mock_instance = MagicMock()
        mock_instance.chunk.return_value = [
            {
                "text": "Chunk 1 content",
                "chunk_id": 0,
                "start_char": 0,
                "end_char": 15,
                "metadata": {"chunk_type": "text", "word_count": 3}
            },
            {
                "text": "Chunk 2 content",
                "chunk_id": 1,
                "start_char": 15,
                "end_char": 30,
                "metadata": {"chunk_type": "text", "word_count": 3}
            }
        ]
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_embedding_manager():
    """Mock EmbeddingManager."""
    with patch("src.ingestion.document_processor.EmbeddingManager") as mock_class:
        mock_instance = MagicMock()
        
        # Mock embed_texts to return numpy array
        mock_instance.embed_texts.return_value = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ])
        
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_docx_document():
    """Mock Document from python-docx."""
    with patch("src.ingestion.document_processor.Document") as mock_doc_class:
        mock_doc = MagicMock()
        
        # Mock paragraphs
        mock_para1 = MagicMock()
        mock_para1.text = "First paragraph content"
        mock_para2 = MagicMock()
        mock_para2.text = "Second paragraph content"
        mock_doc.paragraphs = [mock_para1, mock_para2]
        
        # Mock tables
        mock_cell1 = MagicMock()
        mock_cell1.text = "Cell 1"
        mock_cell2 = MagicMock()
        mock_cell2.text = "Cell 2"
        
        mock_row = MagicMock()
        mock_row.cells = [mock_cell1, mock_cell2]
        
        mock_table = MagicMock()
        mock_table.rows = [mock_row]
        
        mock_doc.tables = [mock_table]
        
        mock_doc_class.return_value = mock_doc
        yield mock_doc


@pytest.fixture
def document_processor(
    mock_config, mock_logger, mock_text_chunker, mock_embedding_manager
):
    """Create DocumentProcessor with all dependencies mocked."""
    from src.ingestion.document_processor import DocumentProcessor
    
    processor = DocumentProcessor(file_path="test_document.docx", batch_size=2)
    
    # Mock collection (since it's not created in __init__)
    mock_collection = MagicMock()
    mock_collection.count.return_value = 10
    mock_collection.add.return_value = None
    mock_collection.get.return_value = {
        "ids": ["doc1_0", "doc1_1"],
        "metadatas": [
            {"document_name": "test.docx"},
            {"document_name": "test.docx"}
        ]
    }
    mock_collection.delete.return_value = None
    mock_collection.query.return_value = {
        "documents": [["Result 1", "Result 2"]],
        "metadatas": [[{"document_name": "test.docx"}, {"document_name": "test.docx"}]],
        "distances": [[0.1, 0.2]]
    }
    
    processor.collection = mock_collection
    
    return processor


# ============================================================================
# TEST CLASS: Initialization Tests
# ============================================================================


class TestDocumentProcessorInitialization:
    """Test DocumentProcessor initialization."""
    
    def test_initialization_with_default_batch_size(
        self, mock_config, mock_logger, mock_text_chunker, mock_embedding_manager
    ):
        """Test initialization with default batch size."""
        from src.ingestion.document_processor import DocumentProcessor
        
        processor = DocumentProcessor(file_path="test.docx")
        
        assert processor.batch_size == 1
        assert processor.file_path == Path("test.docx")
        assert processor.chroma_db_path == "./test_chroma_db"
        assert processor.collection_name == "test_collection"
        assert processor.embedding_model == "test-model"
    
    def test_initialization_with_custom_batch_size(
        self, mock_config, mock_logger, mock_text_chunker, mock_embedding_manager
    ):
        """Test initialization with custom batch size."""
        from src.ingestion.document_processor import DocumentProcessor
        
        processor = DocumentProcessor(file_path="test.docx", batch_size=4)
        
        assert processor.batch_size == 4
    
    def test_initialization_creates_text_chunker(
        self, mock_config, mock_logger, mock_text_chunker, mock_embedding_manager
    ):
        """Test that TextChunker is initialized."""
        from src.ingestion.document_processor import DocumentProcessor
        
        processor = DocumentProcessor(file_path="test.docx")
        
        assert processor.chunker is not None
    
    def test_initialization_creates_embedding_manager(
        self, mock_config, mock_logger, mock_text_chunker, mock_embedding_manager
    ):
        """Test that EmbeddingManager is initialized."""
        from src.ingestion.document_processor import DocumentProcessor
        
        processor = DocumentProcessor(file_path="test.docx")
        
        assert processor.embedding_manager is not None
    
    def test_initialization_converts_string_to_path(
        self, mock_config, mock_logger, mock_text_chunker, mock_embedding_manager
    ):
        """Test that file_path string is converted to Path object."""
        from src.ingestion.document_processor import DocumentProcessor
        
        processor = DocumentProcessor(file_path="documents/test.docx")
        
        assert isinstance(processor.file_path, Path)
        assert processor.file_path == Path("documents/test.docx")


# ============================================================================
# TEST CLASS: Document Reading Tests
# ============================================================================


class TestDocumentReading:
    """Test document reading functionality."""
    
    def test_read_docx_with_paragraphs_only(
        self, document_processor, mock_docx_document
    ):
        """Test reading DOCX with only paragraphs."""
        # Modify mock to have no tables
        mock_docx_document.tables = []
        
        content = document_processor._DocumentProcessor__read()
        
        assert "First paragraph content" in content
        assert "Second paragraph content" in content
    
    def test_read_docx_with_tables(
        self, document_processor, mock_docx_document
    ):
        """Test reading DOCX with tables."""
        content = document_processor._DocumentProcessor__read()
        
        # Should include table data
        assert "Cell 1 | Cell 2" in content
    
    def test_read_docx_skips_empty_paragraphs(
        self, document_processor, mock_docx_document
    ):
        """Test that empty paragraphs are skipped."""
        # Add empty paragraph
        empty_para = MagicMock()
        empty_para.text = "   "
        mock_docx_document.paragraphs.append(empty_para)
        
        content = document_processor._DocumentProcessor__read()
        
        # Should not have excessive whitespace
        assert "\n\n\n\n" not in content
    
    def test_read_docx_skips_empty_table_cells(
        self, document_processor, mock_docx_document
    ):
        """Test that empty table cells are handled."""
        # Add empty cell
        empty_cell = MagicMock()
        empty_cell.text = ""
        mock_docx_document.tables[0].rows[0].cells.append(empty_cell)
        
        content = document_processor._DocumentProcessor__read()
        
        assert isinstance(content, str)
    
    def test_read_docx_raises_error_on_empty_document(
        self, document_processor, mock_docx_document
    ):
        """Test that error is raised for empty documents."""
        # Make all paragraphs empty
        for para in mock_docx_document.paragraphs:
            para.text = ""
        mock_docx_document.tables = []
        
        with pytest.raises(ValueError, match="No text content found"):
            document_processor._DocumentProcessor__read()
    
    def test_read_docx_handles_file_not_found(self, document_processor):
        """Test handling of missing file."""
        with patch("src.ingestion.document_processor.Document") as mock_doc:
            mock_doc.side_effect = FileNotFoundError("File not found")
            
            with pytest.raises(RuntimeError, match="Error loading DOCX file"):
                document_processor._DocumentProcessor__read()
    
    def test_read_docx_handles_corrupted_file(self, document_processor):
        """Test handling of corrupted DOCX file."""
        with patch("src.ingestion.document_processor.Document") as mock_doc:
            mock_doc.side_effect = Exception("Corrupted file")
            
            with pytest.raises(RuntimeError, match="Error loading DOCX file"):
                document_processor._DocumentProcessor__read()
    
    def test_read_docx_multiple_tables(
        self, document_processor, mock_docx_document
    ):
        """Test reading multiple tables."""
        # Add another table
        mock_cell3 = MagicMock()
        mock_cell3.text = "Cell 3"
        mock_row2 = MagicMock()
        mock_row2.cells = [mock_cell3]
        mock_table2 = MagicMock()
        mock_table2.rows = [mock_row2]
        
        mock_docx_document.tables.append(mock_table2)
        
        content = document_processor._DocumentProcessor__read()
        
        assert "Cell 1 | Cell 2" in content
        assert "Cell 3" in content


# ============================================================================
# TEST CLASS: Process Document File Tests
# ============================================================================


class TestProcessDocumentFile:
    """Test complete document processing workflow."""
    
    def test_process_document_file_success(
        self, document_processor, mock_docx_document, 
        mock_text_chunker, mock_embedding_manager
    ):
        """Test successful document processing."""
        result = document_processor.process_document_file()
        
        assert result["status"] == "success"
        assert result["file"] == "test_document.docx"
        assert result["chunks_created"] == 2
        assert result["chunks_stored"] == 2
        assert "content_size" in result
    
    def test_process_document_file_calls_delete_existing(
        self, document_processor, mock_docx_document
    ):
        """Test that existing chunks are deleted before processing."""
        with patch.object(document_processor, 'delete_document_chunks') as mock_delete:
            mock_delete.return_value = 5
            
            document_processor.process_document_file()
            
            mock_delete.assert_called_once_with("test_document.docx")
    
    def test_process_document_file_chunks_text(
        self, document_processor, mock_docx_document, mock_text_chunker
    ):
        """Test that text is chunked."""
        document_processor.process_document_file()
        
        mock_text_chunker.chunk.assert_called_once()
        # Verify content was passed
        call_args = mock_text_chunker.chunk.call_args[0]
        assert isinstance(call_args[0], str)
    
    def test_process_document_file_generates_embeddings(
        self, document_processor, mock_docx_document, mock_embedding_manager
    ):
        """Test that embeddings are generated."""
        document_processor.process_document_file()
        
        mock_embedding_manager.embed_texts.assert_called_once()
        # Verify chunk texts were passed
        call_args = mock_embedding_manager.embed_texts.call_args[0]
        assert isinstance(call_args[0], list)
    
    def test_process_document_file_adds_to_chromadb(
        self, document_processor, mock_docx_document
    ):
        """Test that chunks are added to ChromaDB."""
        document_processor.process_document_file()
        
        document_processor.collection.add.assert_called_once()
        
        # Verify call parameters
        call_kwargs = document_processor.collection.add.call_args[1]
        assert "ids" in call_kwargs
        assert "documents" in call_kwargs
        assert "metadatas" in call_kwargs
        assert "embeddings" in call_kwargs
    
    def test_process_document_file_creates_correct_ids(
        self, document_processor, mock_docx_document
    ):
        """Test that correct IDs are created."""
        document_processor.process_document_file()
        
        call_kwargs = document_processor.collection.add.call_args[1]
        ids = call_kwargs["ids"]
        
        assert len(ids) == 2
        assert ids[0] == "test_document_0"
        assert ids[1] == "test_document_1"
    
    def test_process_document_file_includes_metadata(
        self, document_processor, mock_docx_document
    ):
        """Test that metadata is properly included."""
        document_processor.process_document_file()
        
        call_kwargs = document_processor.collection.add.call_args[1]
        metadatas = call_kwargs["metadatas"]
        
        assert len(metadatas) == 2
        assert metadatas[0]["document_name"] == "test_document.docx"
        assert metadatas[0]["document_stem"] == "test_document"
        assert metadatas[0]["embedding_model"] == "test-model"
    
    def test_process_document_file_handles_read_error(
        self, document_processor
    ):
        """Test handling of document reading error."""
        with patch.object(document_processor, '_DocumentProcessor__read') as mock_read:
            mock_read.side_effect = RuntimeError("Read failed")
            
            result = document_processor.process_document_file()
            
            assert result["status"] == "error"
            assert "error" in result
    
    def test_process_document_file_handles_chunking_error(
        self, document_processor, mock_docx_document, mock_text_chunker
    ):
        """Test handling of chunking error."""
        mock_text_chunker.chunk.side_effect = Exception("Chunking failed")
        
        result = document_processor.process_document_file()
        
        assert result["status"] == "error"
    
    def test_process_document_file_handles_embedding_error(
        self, document_processor, mock_docx_document, mock_embedding_manager
    ):
        """Test handling of embedding generation error."""
        mock_embedding_manager.embed_texts.side_effect = Exception("Embedding failed")
        
        result = document_processor.process_document_file()
        
        assert result["status"] == "error"
    
    def test_process_document_file_handles_chromadb_error(
        self, document_processor, mock_docx_document
    ):
        """Test handling of ChromaDB error."""
        document_processor.collection.add.side_effect = Exception("DB failed")
        
        result = document_processor.process_document_file()
        
        assert result["status"] == "error"
    
    def test_process_document_file_with_numpy_embeddings(
        self, document_processor, mock_docx_document, mock_embedding_manager
    ):
        """Test that numpy embeddings are converted to list."""
        # Mock to return numpy array
        mock_embedding_manager.embed_texts.return_value = np.array([
            [0.1, 0.2],
            [0.3, 0.4]
        ])
        
        document_processor.process_document_file()
        
        call_kwargs = document_processor.collection.add.call_args[1]
        embeddings = call_kwargs["embeddings"]
        
        # Should be converted to list
        assert isinstance(embeddings, list)


# ============================================================================
# TEST CLASS: Search Tests
# ============================================================================


class TestSearch:
    """Test search functionality."""
    
    def test_search_returns_formatted_results(self, document_processor):
        """Test that search returns properly formatted results."""
        results = document_processor.search("test query", top_k=2)
        
        assert len(results) == 2
        assert results[0]["rank"] == 1
        assert results[1]["rank"] == 2
    
    def test_search_includes_content(self, document_processor):
        """Test that search results include content."""
        results = document_processor.search("test query")
        
        assert "content" in results[0]
        assert results[0]["content"] == "Result 1"
    
    def test_search_includes_relevance_score(self, document_processor):
        """Test that relevance score is calculated correctly."""
        results = document_processor.search("test query")
        
        # Distance 0.1 -> relevance 0.9
        assert "relevance_score" in results[0]
        assert results[0]["relevance_score"] == pytest.approx(0.9)
    
    def test_search_includes_metadata_by_default(self, document_processor):
        """Test that metadata is included by default."""
        results = document_processor.search("test query")
        
        assert results[0]["metadata"] is not None
        assert "document_name" in results[0]["metadata"]
    
    def test_search_excludes_metadata_when_requested(self, document_processor):
        """Test that metadata can be excluded."""
        results = document_processor.search("test query", include_metadata=False)
        
        assert results[0]["metadata"] is None
    
    def test_search_respects_top_k_parameter(self, document_processor):
        """Test that top_k parameter is respected."""
        document_processor.search("test query", top_k=5)
        
        call_kwargs = document_processor.collection.query.call_args[1]
        assert call_kwargs["n_results"] == 5
    
    def test_search_handles_empty_results(self, document_processor):
        """Test handling of empty search results."""
        document_processor.collection.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }
        
        results = document_processor.search("test query")
        
        assert results == []
    
    def test_search_handles_query_error(self, document_processor, mock_logger):
        """Test handling of query error."""
        document_processor.collection.query.side_effect = Exception("Query failed")
        
        with pytest.raises(Exception, match="Query failed"):
            document_processor.search("test query")


# ============================================================================
# TEST CLASS: Collection Statistics Tests
# ============================================================================


class TestGetCollectionStats:
    """Test collection statistics retrieval."""
    
    def test_get_collection_stats_returns_dict(self, document_processor):
        """Test that stats returns a dictionary."""
        stats = document_processor.get_collection_stats()
        
        assert isinstance(stats, dict)
    
    def test_get_collection_stats_includes_collection_name(self, document_processor):
        """Test that collection name is included."""
        stats = document_processor.get_collection_stats()
        
        assert stats["collection_name"] == "test_collection"
    
    def test_get_collection_stats_includes_document_count(self, document_processor):
        """Test that document count is included."""
        stats = document_processor.get_collection_stats()
        
        assert stats["total_documents"] == 10
    
    def test_get_collection_stats_includes_embedding_model(self, document_processor):
        """Test that embedding model is included."""
        stats = document_processor.get_collection_stats()
        
        assert stats["embedding_model"] == "test-model"
    
    def test_get_collection_stats_includes_chroma_path(self, document_processor):
        """Test that ChromaDB path is included."""
        stats = document_processor.get_collection_stats()
        
        assert stats["chroma_db_path"] == "./test_chroma_db"
    
    def test_get_collection_stats_handles_error(
        self, document_processor, mock_logger
    ):
        """Test handling of stats retrieval error."""
        document_processor.collection.count.side_effect = Exception("Count failed")
        
        with pytest.raises(Exception, match="Count failed"):
            document_processor.get_collection_stats()


# ============================================================================
# TEST CLASS: Delete Document Chunks Tests
# ============================================================================


class TestDeleteDocumentChunks:
    """Test document chunk deletion."""
    
    def test_delete_document_chunks_queries_by_name(self, document_processor):
        """Test that correct document name is queried."""
        document_processor.delete_document_chunks("test.docx")
        
        call_kwargs = document_processor.collection.get.call_args[1]
        assert call_kwargs["where"] == {"document_name": "test.docx"}
    
    def test_delete_document_chunks_deletes_found_ids(self, document_processor):
        """Test that found IDs are deleted."""
        document_processor.delete_document_chunks("test.docx")
        
        document_processor.collection.delete.assert_called_once_with(
            ids=["doc1_0", "doc1_1"]
        )
    
    def test_delete_document_chunks_returns_count(self, document_processor):
        """Test that deletion count is returned."""
        count = document_processor.delete_document_chunks("test.docx")
        
        assert count == 2
    
    def test_delete_document_chunks_handles_no_results(
        self, document_processor, mock_logger
    ):
        """Test handling when no chunks found."""
        document_processor.collection.get.return_value = {"ids": []}
        
        count = document_processor.delete_document_chunks("nonexistent.docx")
        
        assert count == 0
        # Should not call delete
        document_processor.collection.delete.assert_not_called()
    
    def test_delete_document_chunks_handles_error(
        self, document_processor, mock_logger
    ):
        """Test handling of deletion error."""
        document_processor.collection.get.side_effect = Exception("Get failed")
        
        with pytest.raises(Exception, match="Get failed"):
            document_processor.delete_document_chunks("test.docx")


# ============================================================================
# TEST CLASS: List Documents Tests
# ============================================================================


class TestListDocuments:
    """Test document listing functionality."""
    
    def test_list_documents_returns_list(self, document_processor):
        """Test that list is returned."""
        docs = document_processor.list_documents()
        
        assert isinstance(docs, list)
    
    def test_list_documents_counts_chunks(self, document_processor):
        """Test that chunks are counted per document."""
        docs = document_processor.list_documents()
        
        assert len(docs) == 1
        assert docs[0]["document_name"] == "test.docx"
        assert docs[0]["chunk_count"] == 2
    
    def test_list_documents_with_multiple_documents(self, document_processor):
        """Test with multiple documents."""
        document_processor.collection.get.return_value = {
            "metadatas": [
                {"document_name": "doc1.docx"},
                {"document_name": "doc1.docx"},
                {"document_name": "doc2.docx"},
                {"document_name": "doc2.docx"},
                {"document_name": "doc2.docx"},
            ]
        }
        
        docs = document_processor.list_documents()
        
        assert len(docs) == 2
        # Should be sorted
        assert docs[0]["document_name"] == "doc1.docx"
        assert docs[0]["chunk_count"] == 2
        assert docs[1]["document_name"] == "doc2.docx"
        assert docs[1]["chunk_count"] == 3
    
    def test_list_documents_handles_empty_collection(self, document_processor):
        """Test with empty collection."""
        document_processor.collection.get.return_value = {"metadatas": []}
        
        docs = document_processor.list_documents()
        
        assert docs == []
    
    def test_list_documents_handles_missing_document_name(self, document_processor):
        """Test with missing document_name in metadata."""
        document_processor.collection.get.return_value = {
            "metadatas": [
                {},  # Missing document_name
                {"document_name": "doc1.docx"}
            ]
        }
        
        docs = document_processor.list_documents()
        
        # Should handle gracefully with "unknown"
        assert len(docs) == 2
        assert any(doc["document_name"] == "unknown" for doc in docs)
    
    def test_list_documents_handles_error(self, document_processor, mock_logger):
        """Test handling of listing error."""
        document_processor.collection.get.side_effect = Exception("Get failed")
        
        with pytest.raises(Exception, match="Get failed"):
            document_processor.list_documents()


# ============================================================================
# TEST CLASS: Get Document Chunk Count Tests
# ============================================================================


class TestGetDocumentChunkCount:
    """Test document chunk count retrieval."""
    
    def test_get_document_chunk_count_returns_count(self, document_processor):
        """Test that count is returned."""
        count = document_processor.get_document_chunk_count("test.docx")
        
        assert count == 2
    
    def test_get_document_chunk_count_queries_by_name(self, document_processor):
        """Test that correct document name is queried."""
        document_processor.get_document_chunk_count("test.docx")
        
        call_kwargs = document_processor.collection.get.call_args[1]
        assert call_kwargs["where"] == {"document_name": "test.docx"}
    
    def test_get_document_chunk_count_with_no_chunks(self, document_processor):
        """Test with document that has no chunks."""
        document_processor.collection.get.return_value = {"ids": []}
        
        count = document_processor.get_document_chunk_count("nonexistent.docx")
        
        assert count == 0
    
    def test_get_document_chunk_count_handles_error(
        self, document_processor, mock_logger
    ):
        """Test handling of count error."""
        document_processor.collection.get.side_effect = Exception("Get failed")
        
        count = document_processor.get_document_chunk_count("test.docx")
        
        # Should return 0 on error (as per implementation)
        assert count == 0


# ============================================================================
# TEST CLASS: Edge Cases and Integration Tests
# ============================================================================


class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios."""
    
    def test_process_document_with_very_long_content(
        self, document_processor, mock_docx_document, mock_text_chunker,
        mock_embedding_manager
    ):
        """Test processing document with very long content."""
        # Mock very long paragraphs
        long_para = MagicMock()
        long_para.text = "word " * 10000
        mock_docx_document.paragraphs = [long_para]
        mock_docx_document.tables = []
        
        # Mock many chunks
        many_chunks = [
            {
                "text": f"Chunk {i}",
                "chunk_id": i,
                "start_char": i * 100,
                "end_char": (i + 1) * 100,
                "metadata": {"chunk_type": "text", "word_count": 10}
            }
            for i in range(100)
        ]
        mock_text_chunker.chunk.return_value = many_chunks
        
        # Mock embeddings for 100 chunks
        mock_embedding_manager.embed_texts.return_value = np.random.rand(100, 384)
        
        result = document_processor.process_document_file()
        
        assert result["status"] == "success"
        assert result["chunks_created"] == 100
    
    def test_process_document_with_special_characters(
        self, document_processor, mock_docx_document
    ):
        """Test processing document with special characters."""
        special_para = MagicMock()
        special_para.text = "Text with émojis 🎉 and spëcial çhars & symbols <>"
        mock_docx_document.paragraphs = [special_para]
        mock_docx_document.tables = []
        
        result = document_processor.process_document_file()
        
        assert result["status"] == "success"
    
    def test_process_document_with_unicode(
        self, document_processor, mock_docx_document
    ):
        """Test processing document with unicode characters."""
        unicode_para = MagicMock()
        unicode_para.text = "你好世界 こんにちは مرحبا"
        mock_docx_document.paragraphs = [unicode_para]
        mock_docx_document.tables = []
        
        result = document_processor.process_document_file()
        
        assert result["status"] == "success"
    
    def test_search_with_special_characters_in_query(self, document_processor):
        """Test search with special characters."""
        results = document_processor.search("query with émojis 🎉")
        
        assert isinstance(results, list)
    
    def test_delete_document_with_special_characters(self, document_processor):
        """Test deleting document with special characters in name."""
        count = document_processor.delete_document_chunks("document_émojis_🎉.docx")
        
        assert isinstance(count, int)
    
    def test_full_workflow_integration(
        self, document_processor, mock_docx_document
    ):
        """Test complete workflow: process, search, delete."""
        # 1. Process document
        result = document_processor.process_document_file()
        assert result["status"] == "success"
        
        # 2. Search
        search_results = document_processor.search("test query")
        assert len(search_results) > 0
        
        # 3. Get stats
        stats = document_processor.get_collection_stats()
        assert stats["total_documents"] > 0
        
        # 4. List documents
        docs = document_processor.list_documents()
        assert len(docs) > 0
        
        # 5. Delete document
        count = document_processor.delete_document_chunks("test_document.docx")
        assert count >= 0


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("batch_size", [1, 2, 4, 8, 16])
    def test_initialization_with_various_batch_sizes(
        self, mock_config, mock_logger, mock_text_chunker,
        mock_embedding_manager, batch_size
    ):
        """Test initialization with various batch sizes."""
        from src.ingestion.document_processor import DocumentProcessor
        
        processor = DocumentProcessor(file_path="test.docx", batch_size=batch_size)
        
        assert processor.batch_size == batch_size
    
    @pytest.mark.parametrize("top_k", [1, 3, 5, 10, 100])
    def test_search_with_various_top_k_values(self, document_processor, top_k):
        """Test search with various top_k values."""
        # Mock different result counts
        result_count = min(top_k, 2)
        mock_results = {
            "documents": [["Result"] * result_count],
            "metadatas": [[{"document_name": "test.docx"}] * result_count],
            "distances": [[0.1] * result_count]
        }
        document_processor.collection.query.return_value = mock_results
        
        results = document_processor.search("query", top_k=top_k)
        
        # Verify query was called with correct top_k
        call_kwargs = document_processor.collection.query.call_args[1]
        assert call_kwargs["n_results"] == top_k
    
    @pytest.mark.parametrize("filename", [
        "test.docx",
        "document_with_spaces.docx",
        "document-with-dashes.docx",
        "document_123.docx",
        "très_long_document_name_with_special_chars_émojis.docx"
    ])
    def test_process_various_filenames(
        self, mock_config, mock_logger, mock_text_chunker,
        mock_embedding_manager, mock_docx_document, filename
    ):
        """Test processing documents with various filenames."""
        from src.ingestion.document_processor import DocumentProcessor
        
        processor = DocumentProcessor(file_path=filename)
        
        # Mock collection
        mock_collection = MagicMock()
        mock_collection.get.return_value = {"ids": []}
        mock_collection.add.return_value = None
        processor.collection = mock_collection
        
        result = processor.process_document_file()
        
        assert result["file"] == filename


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.ingestion.document_processor",
        "--cov-report=term-missing"
    ])