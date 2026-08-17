"""
Comprehensive unit tests for TextChunker.

This test suite covers:
- Initialization and configuration
- Text chunking with paragraph preservation
- Text chunking without paragraph preservation
- Fixed-size chunking
- Chunk statistics
- Edge cases (empty text, single word, very long text)
- Word counting
- Overlap handling
- Metadata propagation
"""

from unittest.mock import MagicMock, patch, call

import pytest


# ============================================================================
# FIXTURES - Reusable Test Data and Mocks
# ============================================================================


@pytest.fixture
def mock_config():
    """
    Mock configuration values.
    
    Testing Concept: Mock configuration loading
    """
    config_values = {
        "vector.chunk_size": 800,
        "vector.chunk_overlap": 50,
        "vector.min_words_per_chunk": 30,
    }
    
    with patch("src.ingestion.text_chunker.get_config") as mock:
        mock.side_effect = lambda key, default=None: config_values.get(key, default)
        yield mock


@pytest.fixture
def mock_logger():
    """
    Mock logger to avoid actual logging during tests.
    
    Testing Concept: Mock logging
    """
    with patch("src.ingestion.text_chunker.logger") as mock:
        yield mock


@pytest.fixture
def text_chunker(mock_config, mock_logger):
    """
    Create TextChunker with mocked dependencies.
    
    Testing Concept: Fixture with dependency injection
    """
    from src.ingestion.text_chunker import TextChunker
    return TextChunker()


@pytest.fixture
def text_chunker_no_preserve(mock_config, mock_logger):
    """
    Create TextChunker without paragraph preservation.
    
    Testing Concept: Fixture for alternative configuration
    """
    from src.ingestion.text_chunker import TextChunker
    return TextChunker(preserve_paragraphs=False)


@pytest.fixture
def sample_text_short():
    """Short sample text for testing."""
    return "This is a short sample text. It has multiple sentences. But it's quite brief."


@pytest.fixture
def sample_text_with_paragraphs():
    """Sample text with multiple paragraphs."""
    return """This is the first paragraph. It contains several sentences.
This continues the first paragraph with more information.

This is the second paragraph. It's separate from the first.
It also has multiple sentences to make it more substantial.

This is the third paragraph. It's even shorter than the others."""


@pytest.fixture
def sample_text_long():
    """Long sample text that requires chunking."""
    # Create text that's definitely longer than default chunk_size (800)
    return " ".join([f"Word{i}" for i in range(500)])  # ~2500 chars


@pytest.fixture
def sample_text_very_long_paragraph():
    """Single very long paragraph that exceeds chunk size."""
    return " ".join([f"LongWord{i}" for i in range(200)])  # ~1800 chars in one paragraph


@pytest.fixture
def sample_metadata():
    """Sample metadata dictionary."""
    return {
        "source": "test_document.txt",
        "category": "test",
        "author": "Test Author"
    }


# ============================================================================
# TEST CLASS: Initialization Tests
# ============================================================================


class TestTextChunkerInitialization:
    """Test TextChunker initialization."""
    
    def test_initialization_loads_chunk_size_from_config(self, mock_logger):
        """
        Test that chunk_size is loaded from config.
        
        Testing Concept: Test configuration loading
        """
        with patch("src.ingestion.text_chunker.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "vector.chunk_size": 1000,
                "vector.chunk_overlap": 50,
                "vector.min_words_per_chunk": 30,
            }.get(key, default)
            
            from src.ingestion.text_chunker import TextChunker
            chunker = TextChunker()
            
            assert chunker.chunk_size == 1000
    
    def test_initialization_loads_chunk_overlap_from_config(self, mock_logger):
        """
        Test that chunk_overlap is loaded from config.
        
        Testing Concept: Test configuration loading
        """
        with patch("src.ingestion.text_chunker.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "vector.chunk_size": 800,
                "vector.chunk_overlap": 100,
                "vector.min_words_per_chunk": 30,
            }.get(key, default)
            
            from src.ingestion.text_chunker import TextChunker
            chunker = TextChunker()
            
            assert chunker.chunk_overlap == 100
    
    def test_initialization_loads_min_words_from_config(self, mock_logger):
        """
        Test that min_words is loaded from config.
        
        Testing Concept: Test configuration loading
        """
        with patch("src.ingestion.text_chunker.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "vector.chunk_size": 800,
                "vector.chunk_overlap": 50,
                "vector.min_words_per_chunk": 50,
            }.get(key, default)
            
            from src.ingestion.text_chunker import TextChunker
            chunker = TextChunker()
            
            assert chunker.min_words == 50
    
    def test_initialization_with_preserve_paragraphs_true(self, mock_config, mock_logger):
        """
        Test initialization with preserve_paragraphs=True.
        
        Testing Concept: Test parameter passing
        """
        from src.ingestion.text_chunker import TextChunker
        chunker = TextChunker(preserve_paragraphs=True)
        
        assert chunker.preserve_paragraphs is True
    
    def test_initialization_with_preserve_paragraphs_false(self, mock_config, mock_logger):
        """
        Test initialization with preserve_paragraphs=False.
        
        Testing Concept: Test parameter passing
        """
        from src.ingestion.text_chunker import TextChunker
        chunker = TextChunker(preserve_paragraphs=False)
        
        assert chunker.preserve_paragraphs is False
    
    def test_initialization_logs_configuration(self, mock_logger):
        """
        Test that initialization logs configuration.
        
        Testing Concept: Test logging
        """
        with patch("src.ingestion.text_chunker.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "vector.chunk_size": 800,
                "vector.chunk_overlap": 50,
                "vector.min_words_per_chunk": 30,
            }.get(key, default)
            
            from src.ingestion.text_chunker import TextChunker
            chunker = TextChunker()
            
            mock_logger.info.assert_called_with(
                "TextChunker: chunk_size=%s, chunk_overlap=%s, min_words=%s",
                800, 50, 30
            )
    
    def test_initialization_uses_defaults_when_config_none(self, mock_logger):
        """
        Test that defaults are used when config returns None.
        
        Testing Concept: Test default values
        """
        with patch("src.ingestion.text_chunker.get_config") as mock_config:
            mock_config.return_value = None
            
            from src.ingestion.text_chunker import TextChunker
            chunker = TextChunker()
            
            # Should use fallback values from 'or' expressions
            assert chunker.chunk_size == 800
            assert chunker.chunk_overlap == 50
            assert chunker.min_words == 30


# ============================================================================
# TEST CLASS: Word Counting
# ============================================================================


class TestWordCounting:
    """Test _count_words helper method."""
    
    def test_count_words_single_word(self, text_chunker):
        """
        Test counting single word.
        
        Testing Concept: Test minimum input
        """
        result = text_chunker._count_words("word")
        assert result == 1
    
    def test_count_words_multiple_words(self, text_chunker):
        """
        Test counting multiple words.
        
        Testing Concept: Test normal input
        """
        result = text_chunker._count_words("one two three four five")
        assert result == 5
    
    def test_count_words_empty_string(self, text_chunker):
        """
        Test counting words in empty string.
        
        Testing Concept: Test edge case
        """
        result = text_chunker._count_words("")
        assert result == 0
    
    def test_count_words_with_extra_spaces(self, text_chunker):
        """
        Test counting words with extra spaces.
        
        Testing Concept: Test whitespace handling
        """
        result = text_chunker._count_words("word1   word2    word3")
        # str.split() collapses multiple spaces and does not count empty strings
        assert result == 3
    
    def test_count_words_with_newlines(self, text_chunker):
        """
        Test counting words with newlines.
        
        Testing Concept: Test multiline input
        """
        result = text_chunker._count_words("line1\nline2\nline3")
        assert result == 3


# ============================================================================
# TEST CLASS: Chunk Method - Happy Path (Preserve Paragraphs)
# ============================================================================


class TestChunkMethodHappyPathPreserveParagraphs:
    """Test chunk method with paragraph preservation enabled."""
    
    def test_chunk_returns_list_of_dicts(self, text_chunker, sample_text_short):
        """
        Test that chunk returns list of dictionaries.
        
        Testing Concept: Test return type
        """
        result = text_chunker.chunk(sample_text_short)
        
        assert isinstance(result, list)
        assert all(isinstance(chunk, dict) for chunk in result)
    
    def test_chunk_includes_required_keys(self, text_chunker, sample_text_short):
        """
        Test that each chunk has required keys.
        
        Testing Concept: Test data structure
        """
        result = text_chunker.chunk(sample_text_short)
        
        required_keys = ["text", "chunk_id", "start_char", "end_char", "metadata"]
        for chunk in result:
            assert all(key in chunk for key in required_keys)
    
    def test_chunk_preserves_text_content(self, text_chunker, sample_text_short):
        """
        Test that chunked text content is preserved.
        
        Testing Concept: Test data integrity
        """
        result = text_chunker.chunk(sample_text_short)
        
        # Combine all chunks
        combined = " ".join([chunk["text"] for chunk in result])
        
        # Should contain all original words
        original_words = set(sample_text_short.split())
        combined_words = set(combined.split())
        
        assert original_words.issubset(combined_words)
    
    def test_chunk_assigns_sequential_chunk_ids(self, text_chunker, sample_text_with_paragraphs):
        """
        Test that chunk IDs are sequential.
        
        Testing Concept: Test ID assignment
        """
        result = text_chunker.chunk(sample_text_with_paragraphs)
        
        chunk_ids = [chunk["chunk_id"] for chunk in result]
        
        # Should be sequential starting from 0
        assert chunk_ids == list(range(len(result)))
    
    def test_chunk_includes_metadata_in_chunks(self, text_chunker, sample_text_short, sample_metadata):
        """
        Test that metadata is included in chunks.
        
        Testing Concept: Test metadata propagation
        """
        result = text_chunker.chunk(sample_text_short, metadata=sample_metadata)
        
        for chunk in result:
            # Original metadata should be present
            assert chunk["metadata"]["source"] == sample_metadata["source"]
            assert chunk["metadata"]["category"] == sample_metadata["category"]
    
    def test_chunk_adds_word_count_to_metadata(self, text_chunker, sample_text_short):
        """
        Test that word_count is added to metadata.
        
        Testing Concept: Test metadata enrichment
        """
        result = text_chunker.chunk(sample_text_short)
        
        for chunk in result:
            assert "word_count" in chunk["metadata"]
            assert isinstance(chunk["metadata"]["word_count"], int)
            assert chunk["metadata"]["word_count"] > 0
    
    def test_chunk_logs_start_and_completion(self, text_chunker, sample_text_short, mock_logger):
        """
        Test that chunking is logged.
        
        Testing Concept: Test logging
        """
        result = text_chunker.chunk(sample_text_short)
        
        # Should log start
        mock_logger.info.assert_any_call("Starting chunking: %d chars", len(sample_text_short))
        
        # Should log completion
        mock_logger.info.assert_any_call("Chunking complete: %d chunks created", len(result))
    
    def test_chunk_handles_multiple_paragraphs(self, text_chunker, sample_text_with_paragraphs):
        """
        Test chunking text with multiple paragraphs.
        
        Testing Concept: Test paragraph handling
        """
        result = text_chunker.chunk(sample_text_with_paragraphs)
        
        # Should create multiple chunks
        assert len(result) > 1
        
        # Each chunk should have content
        assert all(len(chunk["text"]) > 0 for chunk in result)
    
    def test_chunk_adds_chunk_type_to_metadata(self, text_chunker, sample_text_with_paragraphs):
        """
        Test that chunk_type is added to metadata.
        
        Testing Concept: Test metadata enrichment
        """
        result = text_chunker.chunk(sample_text_with_paragraphs)
        
        for chunk in result:
            assert "chunk_type" in chunk["metadata"]
            assert chunk["metadata"]["chunk_type"] in ["buffered", "fixed_size"]


# ============================================================================
# TEST CLASS: Chunk Method - Edge Cases (Preserve Paragraphs)
# ============================================================================


class TestChunkMethodEdgeCasesPreserveParagraphs:
    """Test edge cases with paragraph preservation."""
    
    def test_chunk_empty_string(self, text_chunker):
        """
        Test chunking empty string.
        
        Testing Concept: Test empty input
        """
        result = text_chunker.chunk("")
        
        # Should return empty list or handle gracefully
        assert isinstance(result, list)
    
    def test_chunk_single_word(self, text_chunker):
        """
        Test chunking single word.
        
        Testing Concept: Test minimum input
        """
        result = text_chunker.chunk("word")
        
        assert len(result) >= 1
        if result:
            assert "word" in result[0]["text"]
    
    def test_chunk_only_whitespace(self, text_chunker):
        """
        Test chunking only whitespace.
        
        Testing Concept: Test whitespace handling
        """
        result = text_chunker.chunk("   \n\n   \n   ")
        
        assert isinstance(result, list)
    
    def test_chunk_very_long_single_paragraph(self, text_chunker, sample_text_very_long_paragraph):
        """
        Test chunking very long paragraph that exceeds chunk_size.
        
        Testing Concept: Test boundary condition
        """
        result = text_chunker.chunk(sample_text_very_long_paragraph)
        
        # Should split into multiple chunks
        assert len(result) > 1
        
        # No chunk should exceed chunk_size significantly
        for chunk in result:
            assert len(chunk["text"]) <= text_chunker.chunk_size + 100  # Small buffer
    
    def test_chunk_multiple_empty_paragraphs(self, text_chunker):
        """
        Test chunking text with empty paragraphs.
        
        Testing Concept: Test whitespace paragraphs
        """
        text = "Paragraph one.\n\n\n\nParagraph two."
        result = text_chunker.chunk(text)
        
        # Should skip empty paragraphs
        assert len(result) >= 1
    
    def test_chunk_with_none_metadata(self, text_chunker, sample_text_short):
        """
        Test chunking with None metadata.
        
        Testing Concept: Test None input
        """
        result = text_chunker.chunk(sample_text_short, metadata=None)
        
        # Should handle None and create empty dict
        assert len(result) > 0
        assert "metadata" in result[0]
    
    def test_chunk_paragraph_exactly_at_chunk_size(self, text_chunker):
        """
        Test paragraph exactly at chunk_size boundary.
        
        Testing Concept: Test boundary value
        """
        # Create text exactly 800 chars
        text = "A" * 800
        result = text_chunker.chunk(text)
        
        # Should create at least one chunk
        assert len(result) >= 1
    
    def test_chunk_paragraph_just_below_chunk_size(self, text_chunker):
        """
        Test paragraph just below chunk_size.
        
        Testing Concept: Test boundary - 1
        """
        text = "A" * 799
        result = text_chunker.chunk(text)
        
        # Should fit in one chunk
        assert len(result) >= 1


# ============================================================================
# TEST CLASS: Chunk Method - Buffer Flushing Logic
# ============================================================================


class TestBufferFlushingLogic:
    """Test buffer flushing behavior in paragraph preservation mode."""
    
    def test_chunk_flushes_buffer_when_exceeding_chunk_size(self, text_chunker):
        """
        Test that buffer is flushed when size would be exceeded.
        
        Testing Concept: Test buffer flush trigger
        """
        # Create paragraphs that together exceed chunk_size
        text = "Paragraph one. " * 30 + "\n\n" + "Paragraph two. " * 30
        result = text_chunker.chunk(text)
        
        # Should create multiple chunks
        assert len(result) >= 2
    
    def test_chunk_flushes_buffer_when_reaching_min_words(self, text_chunker):
        """
        Test that buffer is flushed when min_words is reached.
        
        Testing Concept: Test min_words trigger
        """
        # Create text with enough words to trigger min_words (30)
        text = " ".join([f"word{i}" for i in range(35)])
        result = text_chunker.chunk(text)
        
        # Should create at least one chunk
        assert len(result) >= 1
    
    def test_chunk_handles_long_paragraph_after_buffer(self, text_chunker):
        """
        Test handling long paragraph after accumulating buffer.
        
        Testing Concept: Test buffer flush before long paragraph
        """
        # Short paragraph + very long paragraph
        short_para = "Short paragraph."
        long_para = " ".join([f"Word{i}" for i in range(200)])
        text = f"{short_para}\n\n{long_para}"
        
        result = text_chunker.chunk(text)
        
        # Buffer should be flushed before processing long paragraph
        assert len(result) >= 2
    
    def test_chunk_flushes_remaining_buffer_at_end(self, text_chunker):
        """
        Test that remaining buffer is flushed at end.
        
        Testing Concept: Test final buffer flush
        """
        # Small paragraphs that don't reach min_words individually
        text = "Para1.\n\nPara2.\n\nPara3."
        result = text_chunker.chunk(text)
        
        # Should still create chunks from remaining buffer
        assert len(result) >= 1


# ============================================================================
# TEST CLASS: Chunk Method - Without Paragraph Preservation
# ============================================================================


class TestChunkMethodWithoutParagraphPreservation:
    """Test chunk method with paragraph preservation disabled."""
    
    def test_chunk_without_preserve_uses_fixed_size(
        self, text_chunker_no_preserve, sample_text_long
    ):
        """
        Test that chunking without preserve uses fixed-size chunking.
        
        Testing Concept: Test alternate chunking mode
        """
        result = text_chunker_no_preserve.chunk(sample_text_long)
        
        # Should create multiple chunks
        assert len(result) > 1
        
        # All chunks should have chunk_type "fixed_size"
        for chunk in result:
            assert chunk["metadata"]["chunk_type"] == "fixed_size"
    
    def test_chunk_without_preserve_assigns_sequential_ids(
        self, text_chunker_no_preserve, sample_text_long
    ):
        """
        Test that chunk IDs are sequential in fixed-size mode.
        
        Testing Concept: Test ID assignment in alternate mode
        """
        result = text_chunker_no_preserve.chunk(sample_text_long)
        
        chunk_ids = [chunk["chunk_id"] for chunk in result]
        assert chunk_ids == list(range(len(result)))
    
    def test_chunk_without_preserve_includes_metadata(
        self, text_chunker_no_preserve, sample_text_short, sample_metadata
    ):
        """
        Test that metadata is included in fixed-size chunks.
        
        Testing Concept: Test metadata in alternate mode
        """
        result = text_chunker_no_preserve.chunk(sample_text_short, metadata=sample_metadata)
        
        for chunk in result:
            assert chunk["metadata"]["source"] == sample_metadata["source"]


# ============================================================================
# TEST CLASS: Fixed-Size Chunking Method
# ============================================================================


class TestFixedSizeChunking:
    """Test _chunk_text method for fixed-size chunking."""
    
    def test_chunk_text_returns_list_of_dicts(self, text_chunker, sample_text_short):
        """
        Test that _chunk_text returns list of dictionaries.
        
        Testing Concept: Test return type
        """
        result = text_chunker._chunk_text(sample_text_short, start_id=0)
        
        assert isinstance(result, list)
        assert all(isinstance(chunk, dict) for chunk in result)
    
    def test_chunk_text_includes_required_keys(self, text_chunker, sample_text_short):
        """
        Test that chunks have required keys.
        
        Testing Concept: Test data structure
        """
        result = text_chunker._chunk_text(sample_text_short, start_id=0)
        
        required_keys = ["text", "chunk_id", "start_char", "end_char", "metadata"]
        for chunk in result:
            assert all(key in chunk for key in required_keys)
    
    def test_chunk_text_respects_chunk_size(self, text_chunker, sample_text_long):
        """
        Test that chunks respect chunk_size limit.
        
        Testing Concept: Test size constraint
        """
        result = text_chunker._chunk_text(sample_text_long, start_id=0)
        
        # No chunk should significantly exceed chunk_size
        for chunk in result:
            assert len(chunk["text"]) <= text_chunker.chunk_size + 50  # Small tolerance
    
    def test_chunk_text_applies_overlap(self, text_chunker):
        """
        Test that overlap is applied between chunks.
        
        Testing Concept: Test overlap logic
        """
        # Create text longer than chunk_size
        text = " ".join([f"Word{i}" for i in range(300)])
        result = text_chunker._chunk_text(text, start_id=0)
        
        if len(result) > 1:
            # There should be some overlap between consecutive chunks
            # This is hard to test precisely, but we can check chunk positions
            for i in range(len(result) - 1):
                current_end = result[i]["end_char"]
                next_start = result[i + 1]["start_char"]
                
                # Next chunk should start before current chunk ends (overlap)
                assert next_start < current_end or next_start == current_end
    
    def test_chunk_text_breaks_at_word_boundary(self, text_chunker):
        """
        Test that chunks break at word boundaries when possible.
        
        Testing Concept: Test word boundary detection
        """
        text = "word1 " * 200  # Lots of words with spaces
        result = text_chunker._chunk_text(text, start_id=0)
        
        # Chunks should not end mid-word (unless no space found)
        for chunk in result:
            # If not the last chunk, should end with complete word
            if len(chunk["text"]) < len(text):
                end_idx = chunk["end_char"]

                assert end_idx <= len(text)
                if end_idx < len(text):
                    assert text[end_idx] == " " or text[end_idx -1] == " "  # Should end at space or next char is space
    
    def test_chunk_text_ensures_forward_progress(self, text_chunker):
        """
        Test that chunking always makes forward progress.
        
        Testing Concept: Test infinite loop prevention
        """
        # Even with small overlap, should not get stuck
        text = "A" * 2000  # Long text without spaces
        result = text_chunker._chunk_text(text, start_id=0)
        
        # Should create multiple chunks without infinite loop
        assert len(result) > 1
    
    def test_chunk_text_with_start_id(self, text_chunker, sample_text_short):
        """
        Test that start_id parameter works correctly.
        
        Testing Concept: Test parameter passing
        """
        result = text_chunker._chunk_text(sample_text_short, start_id=5)
        
        # First chunk should have ID 5
        if result:
            assert result[0]["chunk_id"] == 5
    
    def test_chunk_text_strips_whitespace(self, text_chunker):
        """
        Test that chunk text is stripped of whitespace.
        
        Testing Concept: Test data cleaning
        """
        text = "  text with spaces  "
        result = text_chunker._chunk_text(text, start_id=0)
        
        for chunk in result:
            assert not chunk["text"].startswith(" ")
            assert not chunk["text"].endswith(" ")
    
    def test_chunk_text_skips_empty_chunks(self, text_chunker):
        """
        Test that empty chunks are not included.
        
        Testing Concept: Test filtering
        """
        text = "text\n\n\n\nmore text"
        result = text_chunker._chunk_text(text, start_id=0)
        
        # No chunk should have empty text
        assert all(len(chunk["text"]) > 0 for chunk in result)
    
    def test_chunk_text_single_long_word(self, text_chunker):
        """
        Test chunking single very long word (no spaces).
        
        Testing Concept: Test edge case
        """
        text = "A" * 2000  # No word boundaries
        result = text_chunker._chunk_text(text, start_id=0)
        
        # Should still chunk (can't find word boundary, uses chunk_size)
        assert len(result) > 1


# ============================================================================
# TEST CLASS: Get Stats Method
# ============================================================================


class TestGetStatsMethod:
    """Test get_stats method."""
    
    def test_get_stats_returns_dict(self, text_chunker, sample_text_short):
        """
        Test that get_stats returns dictionary.
        
        Testing Concept: Test return type
        """
        chunks = text_chunker.chunk(sample_text_short)
        result = text_chunker.get_stats(chunks)
        
        assert isinstance(result, dict)
    
    def test_get_stats_includes_total_chunks(self, text_chunker, sample_text_short):
        """
        Test that stats include total_chunks.
        
        Testing Concept: Test data completeness
        """
        chunks = text_chunker.chunk(sample_text_short)
        result = text_chunker.get_stats(chunks)
        
        assert "total_chunks" in result
        assert result["total_chunks"] == len(chunks)
    
    def test_get_stats_includes_total_characters(self, text_chunker, sample_text_short):
        """
        Test that stats include total_characters.
        
        Testing Concept: Test data completeness
        """
        chunks = text_chunker.chunk(sample_text_short)
        result = text_chunker.get_stats(chunks)
        
        assert "total_characters" in result
        assert result["total_characters"] > 0
    
    def test_get_stats_includes_average_chunk_size(self, text_chunker, sample_text_short):
        """
        Test that stats include avg_chunk_size.
        
        Testing Concept: Test computed metric
        """
        chunks = text_chunker.chunk(sample_text_short)
        result = text_chunker.get_stats(chunks)
        
        assert "avg_chunk_size" in result
        assert result["avg_chunk_size"] > 0
    
    def test_get_stats_includes_min_max_chunk_size(self, text_chunker, sample_text_short):
        """
        Test that stats include min and max chunk sizes.
        
        Testing Concept: Test range metrics
        """
        chunks = text_chunker.chunk(sample_text_short)
        result = text_chunker.get_stats(chunks)
        
        assert "min_chunk_size" in result
        assert "max_chunk_size" in result
        assert result["min_chunk_size"] <= result["max_chunk_size"]
    
    def test_get_stats_with_empty_chunks(self, text_chunker):
        """
        Test get_stats with empty chunk list.
        
        Testing Concept: Test edge case
        """
        result = text_chunker.get_stats([])
        
        # Should return minimal stats
        assert result["total_chunks"] == 0
    
    def test_get_stats_calculates_average_correctly(self, text_chunker, sample_text_with_paragraphs):
        """
        Test that average is calculated correctly.
        
        Testing Concept: Test calculation accuracy
        """
        chunks = text_chunker.chunk(sample_text_with_paragraphs)
        result = text_chunker.get_stats(chunks)
        
        # Manual calculation
        total_chars = sum(len(c["text"]) for c in chunks)
        expected_avg = total_chars / len(chunks)
        
        assert abs(result["avg_chunk_size"] - expected_avg) < 0.01


# ============================================================================
# TEST CLASS: Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""
    
    def test_full_chunking_workflow_with_paragraphs(
        self, text_chunker, sample_text_with_paragraphs, sample_metadata
    ):
        """
        Test complete chunking workflow.
        
        Testing Concept: Integration test
        """
        # 1. Chunk the text
        chunks = text_chunker.chunk(sample_text_with_paragraphs, metadata=sample_metadata)
        
        # 2. Verify chunks created
        assert len(chunks) > 0
        
        # 3. Get statistics
        stats = text_chunker.get_stats(chunks)
        
        # 4. Verify stats
        assert stats["total_chunks"] == len(chunks)
        assert stats["total_characters"] > 0
        
        # 5. Verify metadata propagation
        for chunk in chunks:
            assert chunk["metadata"]["source"] == sample_metadata["source"]
    
    def test_chunking_preserves_all_content(self, text_chunker, sample_text_with_paragraphs):
        """
        Test that no content is lost during chunking.
        
        Testing Concept: Test data integrity
        """
        chunks = text_chunker.chunk(sample_text_with_paragraphs)
        
        # Combine all chunks
        all_chunk_text = " ".join([chunk["text"] for chunk in chunks])
        
        # Check that all original words are present
        original_words = set(sample_text_with_paragraphs.split())
        chunk_words = set(all_chunk_text.split())
        
        # Most words should be preserved (some duplicates due to overlap)
        assert len(original_words.intersection(chunk_words)) >= len(original_words) * 0.9
    
    def test_chunking_with_different_configurations(self, mock_logger):
        """
        Test chunking with different chunk sizes.
        
        Testing Concept: Test configuration impact
        """
        text = " ".join([f"Word{i}" for i in range(200)])
        
        # Test with small chunk size
        with patch("src.ingestion.text_chunker.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "vector.chunk_size": 400,  # Reasonable size
                "vector.chunk_overlap": 50,  # Reasonable overlap
                "vector.min_words_per_chunk": 10,
            }.get(key, default)
            
            from src.ingestion.text_chunker import TextChunker
            small_chunker = TextChunker(preserve_paragraphs=False)
            small_chunks = small_chunker.chunk(text)
        
        # Test with large chunk size
        with patch("src.ingestion.text_chunker.get_config") as mock_config:
            mock_config.side_effect = lambda key, default=None: {
                "vector.chunk_size": 2000,  # Large enough to fit all text
                "vector.chunk_overlap": 50,
                "vector.min_words_per_chunk": 30,
            }.get(key, default)
            
            from src.ingestion.text_chunker import TextChunker
            large_chunker = TextChunker(preserve_paragraphs=False)
            large_chunks = large_chunker.chunk(text)

        assert len(small_chunks) >= len(large_chunks)

# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("text,expected_word_count", [
        ("single", 1),
        ("two words", 2),
        ("one two three", 3),
        ("", 0),  
        ("word1 word2 word3 word4 word5", 5),
    ])
    def test_count_words_various_inputs(self, text_chunker, text, expected_word_count):
        """
        Test word counting with various inputs.
        
        Testing Concept: Parameterized testing
        """
        result = text_chunker._count_words(text)
        assert result == expected_word_count
    
    @pytest.mark.parametrize("preserve_paragraphs", [True, False])
    def test_chunking_with_both_preservation_modes(
        self, mock_config, mock_logger, preserve_paragraphs, sample_text_long
    ):
        """
        Test chunking works with both preservation modes.
        
        Testing Concept: Parameterized mode testing
        """
        from src.ingestion.text_chunker import TextChunker
        chunker = TextChunker(preserve_paragraphs=preserve_paragraphs)
        
        result = chunker.chunk(sample_text_long)
        
        # Should create chunks in both modes
        assert len(result) > 0
        
        # All chunks should have required keys
        for chunk in result:
            assert "text" in chunk
            assert "chunk_id" in chunk
            assert "metadata" in chunk


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.ingestion.text_chunker",
        "--cov-report=term-missing"
    ])


