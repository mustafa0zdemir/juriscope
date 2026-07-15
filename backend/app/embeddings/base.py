from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """
        Takes a string and returns a vector embedding.
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """
        Returns the embedding dimension of the model.
        """
        pass
