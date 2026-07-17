from abc import ABC, abstractmethod


class RerankProviderError(RuntimeError):
    """Re-ranking provider çağrısındaki hatayı temsil eder."""


class RerankTimeoutError(RerankProviderError):
    """Re-ranking provider çağrısı zaman aşımına uğradığında yükseltilir."""


class RerankProvider(ABC):
    @abstractmethod
    def score(self, question: str, passages: list[str]) -> list[float]:
        """Soru-passage çiftleri için Cross Encoder skorları döndürür."""
