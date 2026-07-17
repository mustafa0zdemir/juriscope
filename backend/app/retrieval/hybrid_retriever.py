from dataclasses import dataclass, field, replace

from sqlalchemy.orm import Session

from app.retrieval.base import SearchResult
from app.retrieval.qdrant_retriever import QdrantRetriever
from app.services.bm25_service import BM25Service


@dataclass(frozen=True)
class RetrievalDebug:
    vector_hits: list[SearchResult]
    keyword_hits: list[SearchResult]
    merged_hits: list[SearchResult]
    reranked_hits: list[SearchResult] = field(default_factory=list)


@dataclass(frozen=True)
class HybridSearchResult:
    results: list[SearchResult]
    debug: RetrievalDebug


class HybridRetriever:
    def __init__(
        self,
        vector_retriever: QdrantRetriever | None = None,
        bm25_service: BM25Service | None = None,
    ) -> None:
        self.vector_retriever = vector_retriever or QdrantRetriever()
        self.bm25_service = bm25_service or BM25Service()

    def search(
        self,
        db: Session,
        question: str,
        contract_ids: list[int],
        query_vector: list[float] | None,
        search_mode: str,
        top_k: int,
    ) -> HybridSearchResult:
        candidate_limit = max(top_k * 3, 20)
        vector_hits: list[SearchResult] = []
        keyword_hits: list[SearchResult] = []

        if search_mode in {"vector", "hybrid"} and query_vector is not None:
            vector_hits = self.vector_retriever.search(
                query_vector=query_vector,
                contract_ids=contract_ids,
                top_k=candidate_limit,
            )

        if search_mode in {"keyword", "hybrid"}:
            keyword_hits = self.bm25_service.search(
                db=db,
                question=question,
                contract_ids=contract_ids,
                top_k=candidate_limit,
            )

        if search_mode == "vector":
            merged_hits = vector_hits
        elif search_mode == "keyword":
            merged_hits = keyword_hits
        else:
            merged_hits = self.merge(vector_hits, keyword_hits)

        results = merged_hits[:top_k]
        return HybridSearchResult(
            results=results,
            debug=RetrievalDebug(
                vector_hits=vector_hits,
                keyword_hits=keyword_hits,
                merged_hits=merged_hits,
                reranked_hits=[],
            ),
        )

    @classmethod
    def merge(
        cls,
        vector_hits: list[SearchResult],
        keyword_hits: list[SearchResult],
    ) -> list[SearchResult]:
        vector_scores = cls._normalize([hit.score for hit in vector_hits])
        keyword_scores = cls._normalize([hit.score for hit in keyword_hits])
        merged: dict[int, SearchResult] = {}

        for hit, normalized_score in zip(vector_hits, vector_scores, strict=True):
            merged[hit.chunk_id] = SearchResult(
                **{
                    **hit.__dict__,
                    "score": normalized_score,
                    "vector_score": hit.score,
                    "hybrid_score": normalized_score,
                }
            )

        for hit, normalized_score in zip(keyword_hits, keyword_scores, strict=True):
            existing = merged.get(hit.chunk_id)
            if existing is None or normalized_score > existing.score:
                merged[hit.chunk_id] = SearchResult(
                    **{
                        **hit.__dict__,
                        "score": normalized_score,
                        "keyword_score": hit.score,
                        "bm25_score": hit.score,
                        "vector_score": existing.vector_score if existing else None,
                        "hybrid_score": normalized_score,
                    }
                )
            elif existing.keyword_score is None:
                merged[hit.chunk_id] = replace(
                    existing,
                    keyword_score=hit.score,
                    bm25_score=hit.score,
                )

        return sorted(merged.values(), key=lambda hit: hit.score, reverse=True)

    @staticmethod
    def _normalize(scores: list[float]) -> list[float]:
        if not scores:
            return []
        minimum = min(scores)
        maximum = max(scores)
        if maximum == minimum:
            return [1.0 for _ in scores]
        return [(score - minimum) / (maximum - minimum) for score in scores]
