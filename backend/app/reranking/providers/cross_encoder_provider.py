import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from threading import Lock
from typing import Any, ClassVar

from app.config.settings import settings
from app.reranking.providers.base_provider import (
    RerankProvider,
    RerankProviderError,
    RerankTimeoutError,
)

logger = logging.getLogger(__name__)


class CrossEncoderProvider(RerankProvider):
    """CPU üzerinde çalışan, süreç boyunca paylaşılan Cross Encoder provider'ı."""

    _instance: ClassVar["CrossEncoderProvider | None"] = None
    _instance_lock: ClassVar[Lock] = Lock()

    def __init__(
        self,
        model: Any | None = None,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.model_name = model_name or settings.rerank_model
        self.timeout_seconds = timeout_seconds or settings.rerank_timeout_seconds
        self._model = model or self._load_model()

    @classmethod
    def get_instance(cls) -> "CrossEncoderProvider":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Testler için singleton cache'ini temizler."""
        with cls._instance_lock:
            cls._instance = None

    def score(self, question: str, passages: list[str]) -> list[float]:
        if not passages:
            return []

        pairs = [(question, passage) for passage in passages]
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cross-encoder")
        future = executor.submit(self._model.predict, pairs, show_progress_bar=False)
        try:
            scores = future.result(timeout=self.timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            logger.warning("Cross Encoder inference timed out after %.1f seconds", self.timeout_seconds)
            raise RerankTimeoutError("Cross Encoder zaman aşımına uğradı") from exc
        except Exception as exc:
            logger.exception("Cross Encoder inference failed")
            raise RerankProviderError("Cross Encoder skor üretemedi") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        numeric_scores = [float(score) for score in scores]
        if len(numeric_scores) != len(passages):
            raise RerankProviderError("Cross Encoder beklenen sayıda skor döndürmedi")
        return numeric_scores

    def _load_model(self) -> Any:
        try:
            from sentence_transformers import CrossEncoder

            logger.info("Cross Encoder modeli CPU üzerinde yükleniyor: %s", self.model_name)
            return CrossEncoder(self.model_name, device="cpu")
        except Exception as exc:
            logger.exception("Cross Encoder modeli yüklenemedi: %s", self.model_name)
            raise RerankProviderError("Cross Encoder modeli yüklenemedi") from exc
