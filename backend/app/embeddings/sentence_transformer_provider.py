import logging

from app.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)

class SentenceTransformerProvider(EmbeddingProvider):
    _instance = None
    _model = None
    _dimension = None

    def __new__(cls, model_name: str = None):
        if cls._instance is None:
            cls._instance = super(SentenceTransformerProvider, cls).__new__(cls)
            if model_name:
                cls._instance._load_model(model_name)
        return cls._instance

    def _load_model(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer model: {model_name} on CPU")
            # Force CPU usage initially. Can be extended to "cuda" if GPU is available later.
            self._model = SentenceTransformer(model_name, device="cpu")
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully. Dimension: {self._dimension}")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model: {str(e)}")
            raise

    def embed_text(self, text: str) -> list[float]:
        if not self._model:
            raise RuntimeError("Model is not loaded.")
        
        # encode returns a numpy array, convert to list of floats
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def get_dimension(self) -> int:
        if not self._dimension:
            raise RuntimeError("Model is not loaded.")
        return self._dimension

    @classmethod
    def get_instance(cls):
        """Returns the initialized singleton instance, if it exists."""
        if cls._instance is None or cls._instance._model is None:
            raise RuntimeError("SentenceTransformerProvider is not initialized. Initialize it first during app startup.")
        return cls._instance
