from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    """Provider contract for a future generation implementation."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate an answer from a fully constructed prompt."""
        raise NotImplementedError

    @abstractmethod
    def generate_stream(self, prompt: str) -> Iterator[str]:
        """Generate an answer as a sequence of text chunks."""
        raise NotImplementedError
