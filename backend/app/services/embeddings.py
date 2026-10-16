from typing import List
import torch
from sentence_transformers import SentenceTransformer
import logging
from ..config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Local embedding service powered by SentenceTransformers.
    Optimized for macOS Apple Silicon (MPS) and CPU.
    """
    _instance = None
    _model = None

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        self.model_name = model_name
        self._ensure_model_loaded()

    def _ensure_model_loaded(self):
        if EmbeddingService._model is None:
            # Check for Apple Silicon MPS or fall back to CPU
            device = "cpu"
            if torch.backends.mps.is_available():
                device = "mps"
            
            logger.info(f"Loading embedding model '{self.model_name}' on device '{device}'...")
            try:
                EmbeddingService._model = SentenceTransformer(self.model_name, device=device)
            except Exception as e:
                logger.warning(f"Failed to load on {device}, falling back to CPU: {e}")
                EmbeddingService._model = SentenceTransformer(self.model_name, device="cpu")
            logger.info("Embedding model loaded successfully.")

    @property
    def model(self) -> SentenceTransformer:
        if EmbeddingService._model is None:
            self._ensure_model_loaded()
        return EmbeddingService._model

    def embed_query(self, query: str) -> List[float]:
        """Generates an embedding vector for a single query string."""
        if not query or not query.strip():
            raise ValueError("Query string cannot be empty.")
        embedding = self.model.encode(query.strip(), convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()

    def embed_documents(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Generates embedding vectors for a list of document chunk texts."""
        if not texts:
            return []
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embeddings.tolist()

    def get_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

# Global singleton helper
_embedding_service_instance = None

def get_embedding_service() -> EmbeddingService:
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance
