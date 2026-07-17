from app.legal_analysis.xai.schemas import ConfidenceLevel
from app.retrieval.base import SearchResult


class ConfidenceBuilder:
    def build(self, model_confidence: float, chunks: list[SearchResult]) -> tuple[int, ConfidenceLevel]:
        if not chunks:
            return 0, ConfidenceLevel.VERY_LOW

        normalized_scores = [self._normalize(chunk.score) for chunk in chunks]
        retrieval_quality = sum(normalized_scores) / len(normalized_scores)
        rerank_scores = [self._normalize(chunk.rerank_score) for chunk in chunks if chunk.rerank_score is not None]
        rerank_quality = sum(rerank_scores) / len(rerank_scores) if rerank_scores else retrieval_quality
        source_types = {self._source_group(chunk) for chunk in chunks}
        source_coverage = len(source_types) / 3
        score = round(
            (self._normalize(model_confidence) * 25)
            + (retrieval_quality * 35)
            + (rerank_quality * 20)
            + (source_coverage * 20)
        )
        bounded_score = max(0, min(100, score))
        return bounded_score, self.level_for_score(bounded_score)

    @staticmethod
    def level_for_score(score: int) -> ConfidenceLevel:
        if score < 20:
            return ConfidenceLevel.VERY_LOW
        if score < 40:
            return ConfidenceLevel.LOW
        if score < 60:
            return ConfidenceLevel.MEDIUM
        if score < 80:
            return ConfidenceLevel.HIGH
        return ConfidenceLevel.VERY_HIGH

    @staticmethod
    def _normalize(value: float | None) -> float:
        return max(0.0, min(1.0, float(value or 0)))

    @staticmethod
    def _source_group(chunk: SearchResult) -> str:
        document_type = chunk.metadata.get("document_type")
        if chunk.source_type == "contract":
            return "contract"
        if document_type in {"SUPREME_COURT", "COUNCIL_OF_STATE", "CONSTITUTIONAL_COURT"}:
            return "case"
        return "law"
