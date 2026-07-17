from app.trustworthy_rag.schemas import (
    CitationCoverage,
    GroundingResult,
    HallucinationLevel,
    HallucinationRisk,
    RetrievalMetrics,
)


class HallucinationRiskService:
    def calculate(
        self,
        metrics: RetrievalMetrics,
        citation_coverage: CitationCoverage,
        grounding: GroundingResult,
    ) -> HallucinationRisk:
        retrieval = self._bounded(metrics.average_similarity)
        rerank = self._bounded(metrics.average_rerank_score or retrieval)
        citation = citation_coverage.coverage_percent / 100
        diversity = min(1.0, len(metrics.context_sources) / 3)
        context = min(1.0, metrics.context_characters / 2000)
        confidence = grounding.score / 100
        quality = (
            retrieval * 0.25
            + rerank * 0.2
            + citation * 0.25
            + diversity * 0.1
            + context * 0.1
            + confidence * 0.1
        )
        score = max(0, min(100, round((1 - quality) * 100)))
        level = HallucinationLevel.LOW if score < 35 else HallucinationLevel.MEDIUM if score < 65 else HallucinationLevel.HIGH
        return HallucinationRisk(
            score=score,
            level=level,
            factors={
                "retrieval_quality": round(retrieval, 4),
                "rerank_quality": round(rerank, 4),
                "citation_coverage": round(citation, 4),
                "source_diversity": round(diversity, 4),
                "context_sufficiency": round(context, 4),
                "grounding_confidence": round(confidence, 4),
            },
        )

    @staticmethod
    def _bounded(value: float) -> float:
        return max(0.0, min(1.0, value))
