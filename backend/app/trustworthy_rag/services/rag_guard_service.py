import re
import math

from app.config.settings import settings
from app.retrieval.base import SearchResult
from app.trustworthy_rag.schemas import (
    GuardrailCheck,
    GuardrailReport,
    RetrievalMetrics,
)


class RAGGuardService:
    INJECTION_PATTERNS = (
        r"ignore (all|previous) instructions",
        r"önceki talimatları (unut|yok say)",
        r"system prompt",
        r"geliştirici mesajını göster",
        r"<script",
    )

    def evaluate(
        self,
        question: str,
        chunks: list[SearchResult],
        context: str,
        search_mode: str,
    ) -> tuple[GuardrailReport, RetrievalMetrics]:
        metrics = self.metrics(chunks, context, search_mode)
        if not settings.enable_rag_guardrails:
            return GuardrailReport(enabled=False, passed=True, prompt_safe=True, checks=[], warnings=[]), metrics

        rerank_available = metrics.reranked_chunks > 0
        prompt_input = f"{question}\n{context}"
        prompt_safe = not any(
            re.search(pattern, prompt_input, flags=re.IGNORECASE)
            for pattern in self.INJECTION_PATTERNS
        )
        checks = [
            self._check("minimum_chunks", metrics.used_chunks, settings.min_context_chunks, metrics.used_chunks >= settings.min_context_chunks),
            self._check("minimum_context_characters", metrics.context_characters, settings.min_context_characters, metrics.context_characters >= settings.min_context_characters),
            self._check("minimum_retrieval_score", round(metrics.average_similarity, 4), settings.min_retrieval_score, metrics.average_similarity >= settings.min_retrieval_score),
            self._check(
                "minimum_rerank_score",
                round(metrics.average_rerank_score, 4) if rerank_available else "not_applicable",
                settings.min_rerank_score,
                not rerank_available or metrics.average_rerank_score >= settings.min_rerank_score,
            ),
            self._check("prompt_security", "safe" if prompt_safe else "blocked", "safe", prompt_safe),
            self._check("source_diversity", len(metrics.context_sources), ">=1", len(metrics.context_sources) >= 1),
        ]
        warnings = []
        if len(metrics.context_sources) == 1:
            warnings.append("Context yalnızca tek kaynak türü içeriyor.")
        failed = [check.name for check in checks if not check.passed]
        if failed:
            warnings.append("Başarısız guardrail kontrolleri: " + ", ".join(failed))
        return GuardrailReport(
            enabled=True,
            passed=not failed,
            prompt_safe=prompt_safe,
            checks=checks,
            warnings=warnings,
        ), metrics

    @staticmethod
    def metrics(chunks: list[SearchResult], context: str, search_mode: str) -> RetrievalMetrics:
        similarities = [RAGGuardService._similarity(chunk) for chunk in chunks]
        rerank_scores = [
            RAGGuardService._normalize_rerank(chunk.rerank_score)
            for chunk in chunks
            if chunk.rerank_score is not None
        ]
        return RetrievalMetrics(
            retrieved_chunks=len(chunks),
            reranked_chunks=len(rerank_scores),
            used_chunks=len(chunks),
            average_similarity=round(sum(similarities) / len(similarities), 4) if similarities else 0.0,
            average_rerank_score=round(sum(rerank_scores) / len(rerank_scores), 4) if rerank_scores else 0.0,
            context_characters=len(context),
            context_sources=sorted({RAGGuardService._source(chunk) for chunk in chunks}),
            search_mode=search_mode,
        )

    @staticmethod
    def _similarity(chunk: SearchResult) -> float:
        value = chunk.vector_score if chunk.vector_score is not None else chunk.hybrid_score
        if value is None:
            value = chunk.score
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _normalize_rerank(value: float) -> float:
        numeric = float(value)
        if 0 <= numeric <= 1:
            return numeric
        return 1 / (1 + math.exp(-max(-60, min(60, numeric))))

    @staticmethod
    def _source(chunk: SearchResult) -> str:
        if chunk.source_type == "contract":
            return "contract"
        document_type = chunk.metadata.get("document_type")
        if document_type in {"SUPREME_COURT", "COUNCIL_OF_STATE", "CONSTITUTIONAL_COURT"}:
            return "case_law"
        return "law"

    @staticmethod
    def _check(name: str, actual, required, passed: bool) -> GuardrailCheck:
        return GuardrailCheck(
            name=name,
            actual=actual,
            required=required,
            passed=passed,
            message="Kontrol başarılı." if passed else "Context veya istek güvenlik eşiğini karşılamıyor.",
        )
