import logging
from dataclasses import replace

from app.reranking.providers.base_provider import RerankProvider, RerankProviderError
from app.reranking.providers.cross_encoder_provider import CrossEncoderProvider
from app.retrieval.base import SearchResult

logger = logging.getLogger(__name__)


class ReRankService:
    """Yetkilendirilmiş retrieval adaylarını Cross Encoder ile yeniden sıralar."""

    def __init__(self, provider: RerankProvider | None = None) -> None:
        self.provider = provider

    def rerank(
        self,
        question: str,
        chunks: list[SearchResult],
        top_n: int,
    ) -> list[SearchResult]:
        candidates = chunks
        if not candidates or top_n <= 0:
            return []

        try:
            provider = self.provider or CrossEncoderProvider.get_instance()
            scores = provider.score(question, [chunk.text for chunk in candidates])
        except RerankProviderError:
            logger.warning("Re-ranking kullanılamıyor; Hybrid Search sıralaması korunuyor")
            return self._fallback(candidates, top_n)
        except Exception:
            logger.exception("Re-ranking beklenmeyen bir hatayla tamamlanamadı")
            return self._fallback(candidates, top_n)

        if len(scores) != len(candidates):
            logger.warning("Re-ranking beklenen sayıda skor döndürmedi; Hybrid sıralaması korunuyor")
            return self._fallback(candidates, top_n)

        reranked = sorted(
            zip(candidates, scores, strict=True),
            key=lambda item: item[1],
            reverse=True,
        )[:top_n]
        return [
            replace(chunk, score=score, rerank_score=score, final_rank=index)
            for index, (chunk, score) in enumerate(reranked, start=1)
        ]

    @staticmethod
    def _fallback(chunks: list[SearchResult], top_n: int) -> list[SearchResult]:
        return [
            replace(chunk, final_rank=index)
            for index, chunk in enumerate(chunks[:top_n], start=1)
        ]
