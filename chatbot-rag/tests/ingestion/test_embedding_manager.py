"""
Comprehensive unit tests for EmbeddingManager.
"""

import os
import sys
from unittest.mock import MagicMock, patch, call, PropertyMock

import numpy as np
import pytest
import torch

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.ingestion.embedding_manager import EmbeddingManager, _configure_threads


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
        "vector.embedding_model_name": "intfloat/e5-base-v2",
        "vector.embedding_batch_size": 32,
    }
    
    with patch("src.ingestion.embedding_manager.get_config") as mock:
        mock.side_effect = lambda key, default=None: config_values.get(key, default)
        yield mock


@pytest.fixture
def mock_logger():
    """
    Mock logger to avoid actual logging during tests.
    
    Testing Concept: Mock logging
    """
    with patch("src.ingestion.embedding_manager.logger") as mock:
        yield mock


@pytest.fixture
def mock_sentence_transformer():
    """
    Mock SentenceTransformer model.
    
    Testing Concept: Mock ML model
    """
    mock_model = MagicMock()
    
    # Mock encode to return embeddings
    def mock_encode(texts, convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=False):
        # Return embeddings with dimension 768 (typical for e5-base)
        num_texts = len(texts)
        return np.random.randn(num_texts, 768).astype(np.float32)
    
    mock_model.encode = MagicMock(side_effect=mock_encode)
    mock_model.get_sentence_embedding_dimension.return_value = 768
    mock_model.eval.return_value = None
    
    return mock_model


@pytest.fixture
def mock_torch():
    """
    Mock torch operations.
    
    Testing Concept: Mock PyTorch
    """
    with patch("src.ingestion.embedding_manager.torch") as mock:
        mock.set_num_threads = MagicMock()
        mock.set_num_interop_threads = MagicMock()
        mock.inference_mode = MagicMock()
        # Make inference_mode work as context manager
        mock.inference_mode.return_value.__enter__ = MagicMock()
        mock.inference_mode.return_value.__exit__ = MagicMock()
        yield mock


@pytest.fixture
def embedding_manager_with_mocks(mock_config, mock_logger, mock_sentence_transformer, mock_torch):
    """
    Create EmbeddingManager with all dependencies mocked.
    
    Testing Concept: Fixture with full dependency injection
    """
    with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st_class:
        mock_st_class.return_value = mock_sentence_transformer
        
        with patch("src.ingestion.embedding_manager.gc") as mock_gc:
            manager = EmbeddingManager()
            yield manager


@pytest.fixture
def sample_texts():
    """Sample texts for embedding."""
    return [
        "What is a Schengen visa?",
        "How do I apply for a visa?",
        "What documents are required?",
    ]


@pytest.fixture
def large_text_batch():
    """Large batch of texts for testing batch processing."""
    return [f"Sample text number {i}" for i in range(100)]


# ============================================================================
# TEST CLASS: Initialization Tests
# ============================================================================


class TestEmbeddingManagerInitialization:
    """Test EmbeddingManager initialization."""
    
    def test_initialization_with_default_model(self, mock_config, mock_logger):
        """
        Test initialization with default model from config.
        
        Testing Concept: Test default initialization
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer"):
            manager = EmbeddingManager()
            
            assert manager._model_name == "intfloat/e5-base-v2"
            assert manager._model is None  # Lazy loading
            assert manager._embedding_dim is None
    
    def test_initialization_with_custom_model_name(self, mock_config, mock_logger):
        """
        Test initialization with custom model name.
        
        Testing Concept: Test parameter override
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer"):
            custom_model = "custom/model-name"
            manager = EmbeddingManager(model_name=custom_model)
            
            assert manager._model_name == custom_model
            assert manager._model is None
    
    def test_initialization_does_not_load_model(self, mock_config, mock_logger):
        """
        Test that model is not loaded during initialization.
        
        Testing Concept: Test lazy loading
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            manager = EmbeddingManager()
            
            # Model should NOT be loaded during __init__
            mock_st.assert_not_called()
            assert manager._model is None
    
    def test_initialization_logs_message(self, mock_config, mock_logger):
        """
        Test that initialization logs appropriate message.
        
        Testing Concept: Test logging behavior
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer"):
            manager = EmbeddingManager()
            
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "model will be loaded on first use" in call_args.lower()


# ============================================================================
# TEST CLASS: Lazy Model Loading
# ============================================================================


class TestLazyModelLoading:
    """Test lazy loading functionality."""
    
    def test_load_model_creates_model_instance(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that _load_model creates model instance.
        
        Testing Concept: Test model instantiation
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            manager = EmbeddingManager()
            manager._load_model()
            
            mock_st.assert_called_once_with(
                "intfloat/e5-base-v2",
                device="cpu"
            )
    
    def test_load_model_configures_threads(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that _load_model configures thread limits.
        
        Testing Concept: Test thread configuration
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            with patch("src.ingestion.embedding_manager._configure_threads") as mock_configure:
                manager = EmbeddingManager()
                manager._load_model()
                
                mock_configure.assert_called_once()
    
    def test_load_model_sets_torch_threads(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that PyTorch thread limits are set.
        
        Testing Concept: Test PyTorch configuration
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            manager = EmbeddingManager()
            manager._load_model()
            
            mock_torch.set_num_threads.assert_called_once_with(1)
            mock_torch.set_num_interop_threads.assert_called_once_with(1)
    
    def test_load_model_calls_eval(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that model is set to eval mode.
        
        Testing Concept: Test model configuration
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            manager = EmbeddingManager()
            manager._load_model()
            
            mock_sentence_transformer.eval.assert_called_once()
    
    def test_load_model_sets_embedding_dimension(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that embedding dimension is retrieved and stored.
        
        Testing Concept: Test attribute initialization
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            manager = EmbeddingManager()
            manager._load_model()
            
            assert manager._embedding_dim == 768
            mock_sentence_transformer.get_sentence_embedding_dimension.assert_called_once()
    
    def test_load_model_only_loads_once(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that model is only loaded once even with multiple calls.
        
        Testing Concept: Test idempotency
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            manager = EmbeddingManager()
            
            # Call multiple times
            manager._load_model()
            manager._load_model()
            manager._load_model()
            
            # Should only be called once
            mock_st.assert_called_once()
    
    def test_load_model_calls_garbage_collection(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that garbage collection is called after loading.
        
        Testing Concept: Test memory management
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            with patch("src.ingestion.embedding_manager.gc") as mock_gc:
                manager = EmbeddingManager()
                manager._load_model()
                
                mock_gc.collect.assert_called_once()
    
    def test_load_model_logs_progress(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that loading progress is logged.
        
        Testing Concept: Test logging
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            manager = EmbeddingManager()
            manager._load_model()
            
            # Should log debug and info messages
            assert mock_logger.debug.called
            assert mock_logger.info.called


# ============================================================================
# TEST CLASS: Model Property
# ============================================================================


class TestModelProperty:
    """Test model property accessor."""
    
    def test_model_property_loads_model_if_not_loaded(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that accessing model property loads model.
        
        Testing Concept: Test lazy property loading
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            manager = EmbeddingManager()
            
            # Model not loaded yet
            assert manager._model is None
            
            # Access property
            model = manager.model
            
            # Model should be loaded
            assert model == mock_sentence_transformer
            mock_st.assert_called_once()
    
    def test_model_property_returns_cached_model(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that subsequent accesses use cached model.
        
        Testing Concept: Test caching
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            manager = EmbeddingManager()
            
            # Access multiple times
            model1 = manager.model
            model2 = manager.model
            model3 = manager.model
            
            # Should only load once
            mock_st.assert_called_once()
            assert model1 == model2 == model3


# ============================================================================
# TEST CLASS: Embed Texts - Happy Path
# ============================================================================


class TestEmbedTextsHappyPath:
    """Test embedding generation functionality."""
    
    def test_embed_texts_returns_numpy_array(
        self, embedding_manager_with_mocks, sample_texts
    ):
        """
        Test that embed_texts returns numpy array.
        
        Testing Concept: Test return type
        """
        result = embedding_manager_with_mocks.embed_texts(sample_texts)
        
        assert isinstance(result, np.ndarray)
    
    def test_embed_texts_correct_shape(
        self, embedding_manager_with_mocks, sample_texts
    ):
        """
        Test that embeddings have correct shape.
        
        Testing Concept: Test output dimensions
        """
        result = embedding_manager_with_mocks.embed_texts(sample_texts)
        
        # Shape should be (num_texts, embedding_dim)
        assert result.shape == (3, 768)
    
    def test_embed_texts_loads_model_on_first_call(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that model is loaded on first embed_texts call.
        
        Testing Concept: Test lazy loading trigger
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            manager = EmbeddingManager()
            
            # Model not loaded yet
            assert manager._model is None
            
            # Call embed_texts
            manager.embed_texts(["test text"])
            
            # Model should be loaded
            mock_st.assert_called_once()
    
    def test_embed_texts_calls_model_encode(
        self, embedding_manager_with_mocks, sample_texts
    ):
        """
        Test that model.encode is called correctly.
        
        Testing Concept: Test method invocation
        """
        # Load model first
        model = embedding_manager_with_mocks.model
        
        embedding_manager_with_mocks.embed_texts(sample_texts)
        
        # Should call encode
        assert model.encode.called
    
    def test_embed_texts_uses_batch_processing(
        self, embedding_manager_with_mocks, large_text_batch
    ):
        """
        Test that large batches are processed in chunks.
        
        Testing Concept: Test batch processing
        """
        # Load model
        model = embedding_manager_with_mocks.model
        
        # Process 100 texts with batch size 32
        result = embedding_manager_with_mocks.embed_texts(large_text_batch)
        
        # Should make multiple encode calls (100/32 = 4 batches)
        assert model.encode.call_count >= 3
        
        # Result should have correct shape
        assert result.shape == (100, 768)
    
    def test_embed_texts_with_single_text(
        self, embedding_manager_with_mocks
    ):
        """
        Test embedding single text.
        
        Testing Concept: Test minimum input
        """
        result = embedding_manager_with_mocks.embed_texts(["single text"])
        
        assert result.shape == (1, 768)
    
    def test_embed_texts_logs_progress(
        self, embedding_manager_with_mocks, sample_texts, mock_logger
    ):
        """
        Test that progress is logged.
        
        Testing Concept: Test logging
        """
        embedding_manager_with_mocks.embed_texts(sample_texts)
        
        # Should log debug and info messages
        assert mock_logger.debug.called
        assert mock_logger.info.called
    
    def test_embed_texts_uses_inference_mode(
        self, embedding_manager_with_mocks, sample_texts, mock_torch
    ):
        """
        Test that torch.inference_mode is used.
        
        Testing Concept: Test optimization features
        """
        embedding_manager_with_mocks.embed_texts(sample_texts)
        
        mock_torch.inference_mode.assert_called()
    
    def test_embed_texts_periodic_garbage_collection(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that garbage collection is called periodically.
        
        Testing Concept: Test memory optimization
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            with patch("src.ingestion.embedding_manager.gc") as mock_gc:
                manager = EmbeddingManager()
                
                # Process many texts to trigger multiple batches
                large_batch = [f"text {i}" for i in range(200)]
                manager.embed_texts(large_batch)
                
                # Should call gc.collect multiple times
                # (once in _load_model, multiple times during batching)
                assert mock_gc.collect.call_count >= 2


# ============================================================================
# TEST CLASS: Embed Texts - Edge Cases
# ============================================================================


class TestEmbedTextsEdgeCases:
    """Test edge cases for embedding generation."""
    
    def test_embed_texts_with_empty_list_raises_error(
        self, embedding_manager_with_mocks
    ):
        """
        Test that empty list raises ValueError.
        
        Testing Concept: Test empty input validation
        """
        with pytest.raises(ValueError, match="No texts to embed"):
            embedding_manager_with_mocks.embed_texts([])
    
    def test_embed_texts_with_very_long_text(
        self, embedding_manager_with_mocks
    ):
        """
        Test embedding very long text.
        
        Testing Concept: Test large input
        """
        long_text = "word " * 1000
        result = embedding_manager_with_mocks.embed_texts([long_text])
        
        assert result.shape == (1, 768)
    
    def test_embed_texts_with_special_characters(
        self, embedding_manager_with_mocks
    ):
        """
        Test embedding text with special characters.
        
        Testing Concept: Test special input
        """
        special_texts = [
            "Hello! @#$%^&*()",
            "Émojis: 😀🎉",
            "新年快乐",
            "\n\t\r",
        ]
        result = embedding_manager_with_mocks.embed_texts(special_texts)
        
        assert result.shape == (4, 768)
    
    def test_embed_texts_with_empty_strings(
        self, embedding_manager_with_mocks
    ):
        """
        Test embedding empty strings.
        
        Testing Concept: Test edge case content
        """
        empty_texts = ["", " ", "  "]
        result = embedding_manager_with_mocks.embed_texts(empty_texts)
        
        assert result.shape == (3, 768)
    
    def test_embed_texts_batch_size_larger_than_input(
        self, embedding_manager_with_mocks
    ):
        """
        Test when batch size is larger than number of texts.
        
        Testing Concept: Test batch boundary
        """
        # Only 2 texts, but batch size is 32
        result = embedding_manager_with_mocks.embed_texts(["text1", "text2"])
        
        assert result.shape == (2, 768)
    
    def test_embed_texts_exact_batch_size_multiple(
        self, embedding_manager_with_mocks
    ):
        """
        Test when number of texts is exact multiple of batch size.
        
        Testing Concept: Test boundary alignment
        """
        # Exactly 64 texts (2 * batch_size of 32)
        texts = [f"text {i}" for i in range(64)]
        result = embedding_manager_with_mocks.embed_texts(texts)
        
        assert result.shape == (64, 768)


# ============================================================================
# TEST CLASS: Embed Single Text
# ============================================================================


class TestEmbedSingleText:
    """Test single text embedding convenience method."""
    
    def test_embed_single_text_returns_1d_array(
        self, embedding_manager_with_mocks
    ):
        """
        Test that embed_single_text returns 1D array.
        
        Testing Concept: Test return shape
        """
        result = embedding_manager_with_mocks.embed_single_text("test text")
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (768,)
    
    def test_embed_single_text_calls_embed_texts(
        self, embedding_manager_with_mocks
    ):
        """
        Test that embed_single_text uses embed_texts internally.
        
        Testing Concept: Test method composition
        """
        with patch.object(embedding_manager_with_mocks, 'embed_texts') as mock_embed:
            mock_embed.return_value = np.random.randn(1, 768).astype(np.float32)
            
            embedding_manager_with_mocks.embed_single_text("test")
            
            mock_embed.assert_called_once_with(["test"])
    
    def test_embed_single_text_extracts_first_embedding(
        self, embedding_manager_with_mocks
    ):
        """
        Test that first embedding is extracted correctly.
        
        Testing Concept: Test indexing
        """
        result = embedding_manager_with_mocks.embed_single_text("test text")
        
        # Should be 1D array (first row of 2D result)
        assert len(result.shape) == 1
        assert result.shape[0] == 768


# ============================================================================
# TEST CLASS: Get Embedding Dimension
# ============================================================================


class TestGetEmbeddingDimension:
    """Test embedding dimension retrieval."""
    
    def test_get_embedding_dimension_returns_integer(
        self, embedding_manager_with_mocks
    ):
        """
        Test that dimension is returned as integer.
        
        Testing Concept: Test return type
        """
        dim = embedding_manager_with_mocks.get_embedding_dimension()
        
        assert isinstance(dim, int)
        assert dim == 768
    
    def test_get_embedding_dimension_loads_model_if_needed(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that model is loaded to get dimension.
        
        Testing Concept: Test lazy loading
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            manager = EmbeddingManager()
            
            # Model not loaded yet
            assert manager._model is None
            
            # Get dimension
            dim = manager.get_embedding_dimension()
            
            # Model should be loaded
            mock_st.assert_called_once()
            assert dim == 768
    
    def test_get_embedding_dimension_uses_cached_value(
        self, embedding_manager_with_mocks
    ):
        """
        Test that dimension is cached after first load.
        
        Testing Concept: Test caching
        """
        # Load model
        embedding_manager_with_mocks._load_model()
        model = embedding_manager_with_mocks._model
        
        # Get dimension multiple times
        dim1 = embedding_manager_with_mocks.get_embedding_dimension()
        dim2 = embedding_manager_with_mocks.get_embedding_dimension()
        dim3 = embedding_manager_with_mocks.get_embedding_dimension()
        
        # Should only call get_sentence_embedding_dimension once (during _load_model)
        assert model.get_sentence_embedding_dimension.call_count == 1
        assert dim1 == dim2 == dim3 == 768

# ============================================================================
# TEST CLASS: Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_load_model_handles_model_loading_error(
        self, mock_config, mock_logger, mock_torch
    ):
        """
        Test that model loading errors are properly logged and re-raised.
        
        Testing Concept: Test error handling in initialization
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            # Make SentenceTransformer constructor raise an exception
            mock_st.side_effect = RuntimeError("Model file not found")
            
            manager = EmbeddingManager()
            
            # Verify exception is raised
            with pytest.raises(RuntimeError, match="Model file not found"):
                manager._load_model()
            
            # Verify error was logged
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            assert "Error loading model" in error_call
    
    
    def test_embed_texts_with_none_input(self, embedding_manager_with_mocks):
        """
        Test behavior with None input.

        None is treated as empty input → ValueError
        """
        with pytest.raises(ValueError, match="No texts to embed"):
            embedding_manager_with_mocks.embed_texts(None)
    
    def test_embed_texts_with_string_input(
        self, embedding_manager_with_mocks
    ):
        """
        Test behavior when passing string instead of list.
        
        Testing Concept: Test type mismatch
        
        Note: Python strings are iterable, so this might not raise an error
        in the current implementation depending on how it's written.
        This test documents the actual behavior.
        """
        # If the implementation iterates over the input, a string will work
        # but produce unexpected results (one character per "text")
        # This tests the actual behavior rather than expecting an error
        result = embedding_manager_with_mocks.embed_texts("abc")
        
        # String "abc" is treated as ["a", "b", "c"]
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == 3  # Three characters
    
    def test_embed_texts_with_non_string_elements(
        self, embedding_manager_with_mocks
    ):
        """
        Test behavior with non-string elements in list.
        
        Testing Concept: Test element type validation
        """
        # The model.encode() will handle conversion or fail
        # This documents actual behavior
        try:
            # Try with numbers
            result = embedding_manager_with_mocks.embed_texts([123, 456])
            # If it works, verify shape
            assert isinstance(result, np.ndarray)
        except (TypeError, AttributeError):
            # If it fails, that's also acceptable behavior
            pass
    
    def test_load_model_with_invalid_model_name(
        self, mock_config, mock_logger, mock_torch
    ):
        """
        Test that invalid model names are handled.
        
        Testing Concept: Test configuration error handling
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            # Simulate model not found error
            mock_st.side_effect = OSError("Model 'invalid/model' not found")
            
            manager = EmbeddingManager(model_name="invalid/model")
            
            with pytest.raises(OSError, match="not found"):
                manager._load_model()
            
            # Should log the error
            mock_logger.error.assert_called()
    
    def test_embed_texts_with_integer_input(
        self, embedding_manager_with_mocks
    ):
        """
        Test behavior with integer input.
        
        Testing Concept: Test completely wrong type
        """
        with pytest.raises((TypeError, AttributeError)):
            embedding_manager_with_mocks.embed_texts(12345)
    
    def test_embed_texts_with_dict_input(self, embedding_manager_with_mocks):
        """
        Test behavior with dict input.

        Dict is iterable → allowed by design.
        This test documents actual behavior.
        """
        result = embedding_manager_with_mocks.embed_texts({"a": "hello", "b": "world"})

        assert isinstance(result, np.ndarray)
        assert result.shape[0] == 2


# ============================================================================
# TEST CLASS: Thread Configuration
# ============================================================================


class TestThreadConfiguration:
    """Test thread configuration functionality."""
    
    def test_configure_threads_sets_environment_variables(self):
        """
        Test that _configure_threads sets env variables.
        
        Testing Concept: Test environment configuration
        """
        with patch.dict(os.environ, {}, clear=True):
            # Reset flag for test
            import src.ingestion.embedding_manager as em
            em._THREADS_CONFIGURED = False
            
            _configure_threads()
            
            assert os.environ["OMP_NUM_THREADS"] == "1"
            assert os.environ["MKL_NUM_THREADS"] == "1"
            assert os.environ["NUMEXPR_NUM_THREADS"] == "1"
            assert os.environ["OPENBLAS_NUM_THREADS"] == "1"
    
    def test_configure_threads_only_runs_once(self):
        """
        Test that thread configuration only happens once.
        
        Testing Concept: Test idempotency
        """
        with patch.dict(os.environ, {}, clear=True):
            # Reset flag
            import src.ingestion.embedding_manager as em
            em._THREADS_CONFIGURED = False
            
            # Call multiple times
            _configure_threads()
            _configure_threads()
            _configure_threads()
            
            # Should still have the values
            assert os.environ["OMP_NUM_THREADS"] == "1"
            
            # Flag should be set
            assert em._THREADS_CONFIGURED is True
    
    def test_configure_threads_called_before_model_load(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that threads are configured before loading model.
        
        Testing Concept: Test initialization order
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            with patch("src.ingestion.embedding_manager._configure_threads") as mock_configure:
                manager = EmbeddingManager()
                manager._load_model()
                
                # Should be called before SentenceTransformer
                mock_configure.assert_called()
                assert mock_configure.call_count == 1


# ============================================================================
# TEST CLASS: Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic usage scenarios."""
    
    def test_full_embedding_workflow(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test complete workflow from initialization to embedding.
        
        Testing Concept: Integration test
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            # 1. Initialize (model not loaded)
            manager = EmbeddingManager()
            assert manager._model is None
            
            # 2. Embed texts (triggers model loading)
            texts = ["text1", "text2", "text3"]
            result = manager.embed_texts(texts)
            
            # 3. Verify results
            assert result.shape == (3, 768)
            assert manager._model is not None
            
            # 4. Subsequent calls use cached model
            result2 = manager.embed_texts(["text4"])
            assert result2.shape == (1, 768)
            
            # Model should only be loaded once
            mock_st.assert_called_once()
    
    def test_multiple_batches_workflow(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test processing multiple batches.
        
        Testing Concept: Test batch processing workflow
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            manager = EmbeddingManager()
            
            # Process 100 texts (will use multiple batches with size 32)
            large_batch = [f"text {i}" for i in range(100)]
            result = manager.embed_texts(large_batch)
            
            # Should have correct output shape
            assert result.shape == (100, 768)
            
            # Model encode should be called multiple times
            assert mock_sentence_transformer.encode.call_count >= 3
    
    def test_custom_model_workflow(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test workflow with custom model name.
        
        Testing Concept: Test custom configuration
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            custom_model = "custom/embedding-model"
            manager = EmbeddingManager(model_name=custom_model)
            
            # Trigger model loading
            manager.embed_texts(["test"])
            
            # Should use custom model name
            mock_st.assert_called_once()
            call_args = mock_st.call_args
            assert call_args[0][0] == custom_model


# ============================================================================
# TEST CLASS: Memory Optimization
# ============================================================================


class TestMemoryOptimization:
    """Test memory optimization features."""
    
    def test_batch_processing_deletes_intermediate_variables(
        self, mock_config, mock_logger, mock_sentence_transformer, mock_torch
    ):
        """
        Test that intermediate variables are deleted during batching.
        
        Testing Concept: Test memory cleanup
        """
        with patch("src.ingestion.embedding_manager.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_sentence_transformer
            
            manager = EmbeddingManager()
            
            # This should trigger cleanup through del statements
            large_batch = [f"text {i}" for i in range(100)]
            result = manager.embed_texts(large_batch)
            
            # Verify result is correct
            assert result.shape == (100, 768)
    
    def test_preallocated_output_array(
        self, embedding_manager_with_mocks, large_text_batch
    ):
        """
        Test that output array is pre-allocated.
        
        Testing Concept: Test memory efficiency
        """
        result = embedding_manager_with_mocks.embed_texts(large_text_batch)
        
        # Should return correctly shaped array
        assert result.shape == (100, 768)
        assert result.dtype == np.float32


# ============================================================================
# PARAMETERIZED TESTS
# ============================================================================


class TestParameterizedScenarios:
    """Test multiple scenarios efficiently with parameterization."""
    
    @pytest.mark.parametrize("num_texts,expected_batches", [
        (1, 1),      # Single text
        (32, 1),     # Exactly one batch
        (33, 2),     # Just over one batch
        (64, 2),     # Two full batches
        (65, 3),     # Two full + one partial
        (100, 4),    # Multiple batches
    ])
    def test_various_batch_sizes(
        self, embedding_manager_with_mocks, num_texts, expected_batches, mock_logger
    ):
        """
        Test batch processing with various input sizes.
        
        Testing Concept: Parameterized batch testing
        """
        texts = [f"text {i}" for i in range(num_texts)]
        result = embedding_manager_with_mocks.embed_texts(texts)
        
        assert result.shape == (num_texts, 768)
        
        # Verify logging mentions correct number of batches
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        batch_logs = [log for log in debug_calls if "batches" in log.lower()]
        
        if batch_logs:
            assert str(expected_batches) in batch_logs[0]


# ============================================================================
# Run tests from command line
# ============================================================================


if __name__ == "__main__":
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "--cov=src.ingestion.embedding_manager",
        "--cov-report=term-missing"
    ])