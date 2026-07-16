from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Provider contract for a future generation implementation."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate an answer from a fully constructed prompt."""
        raise NotImplementedError
