"""Memory-optimized embedding manager with LAZY LOADING.

The model is NOT loaded until embed_texts() is called for the first time.
This prevents memory pressure during document loading and chunking.
"""

import gc
import os
from typing import List

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from src.utils import get_config
from src.utils.log_helper import logger

# Flag to track if we've set up thread limits
_THREADS_CONFIGURED = False


def _configure_threads():
    """Configure thread limits BEFORE importing torch."""
    global _THREADS_CONFIGURED
    if _THREADS_CONFIGURED:
        return

    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    _THREADS_CONFIGURED = True


class EmbeddingManager:
    """Manages embedding generation with lazy model loading."""

    def __init__(self, model_name: str = None):
        """
        Initialize embedding manager (model NOT loaded yet).

        Args:
            model_name: Optional model name override
        """
        # Store config but DON'T load model yet
        if model_name:
            self._model_name = model_name
        else:
            from src.utils.config_loader import get_config

            self._model_name = get_config("vector.embedding_model_name")

        self._model = None  # Lazy loaded
        self._embedding_dim = None

        logger.info("EmbeddingManager initialized (model will be loaded on first use)")

    def _load_model(self):
        """Load the model lazily when first needed."""
        if self._model is not None:
            return

        logger.debug("Loading embedding model: %s", self._model_name)

        # Configure threads before torch import
        _configure_threads()

        # Limit PyTorch threads
        try:
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
        except RuntimeError as e:
            logger.debug(f"Could not set PyTorch threads: {e}")

        try:
            # Load model
            self._model = SentenceTransformer(self._model_name, device="cpu")
            self._model.eval()

            # Get embedding dimension
            self._embedding_dim = self._model.get_sentence_embedding_dimension()

            logger.info("Model loaded. Embedding dimension: %s", self._embedding_dim)
            gc.collect()

        except Exception as e:
            logger.error("Error loading model: %s", str(e))
            raise

    @property
    def model(self):
        """Get the model, loading it if necessary."""
        self._load_model()
        return self._model

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings with minimal memory usage.

        Args:
            texts: List of text strings to embed

        Returns:
            numpy array of embeddings
        """
        if not texts:
            raise ValueError("No texts to embed")

        # Load model on first use
        self._load_model()

        num_texts = len(texts)
        batch_size = get_config("vector.embedding_batch_size")
        total_batches = (num_texts + batch_size - 1) // batch_size

        logger.debug(f"Embedding {num_texts} texts in {total_batches} batches")

        # Pre-allocate output
        embeddings = np.zeros((num_texts, self._embedding_dim), dtype=np.float32)

        with torch.inference_mode():
            for i in range(0, num_texts, batch_size):
                batch_start = i
                batch_end = min(i + batch_size, num_texts)
                batch_num = (i // batch_size) + 1

                # Log every 10 batches
                if batch_num % 10 == 0 or batch_num == 1 or batch_num == total_batches:
                    logger.debug(f"Batch {batch_num}/{total_batches}")

                batch_texts = texts[batch_start:batch_end]

                batch_embeddings = self._model.encode(
                    batch_texts,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    normalize_embeddings=False,
                )

                embeddings[batch_start:batch_end] = batch_embeddings

                del batch_texts, batch_embeddings

                if batch_num % 5 == 0:
                    gc.collect()

        logger.info(f"Completed: {num_texts} embeddings")
        return embeddings

    def embed_single_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.embed_texts([text])[0]

    def get_embedding_dimension(self) -> int:
        """Get dimension of embeddings (loads model if needed)."""
        self._load_model()
        return self._embedding_dim
