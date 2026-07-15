from abc import ABC, abstractmethod


class ChunkStrategy(ABC):

    @abstractmethod
    def chunk(self, text: str) -> list[str]:
        """
        Splits the given text into chunks based on the strategy.
        Returns a list of string chunks.
        """
        pass
