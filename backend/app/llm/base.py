from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any


class LLMProvider(ABC):
    """Provider contract for a future generation implementation."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate an answer from a fully constructed prompt."""
        raise NotImplementedError

    def generate_json(self, prompt: str, response_schema: Any) -> str:
        """Generate JSON conforming to a provider-supported schema."""
        return self.generate(prompt)

    @abstractmethod
    def generate_stream(self, prompt: str) -> Iterator[str]:
        """Generate an answer as a sequence of text chunks."""
        raise NotImplementedError
