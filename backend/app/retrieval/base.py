from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    score: float
    chunk_id: int
    contract_id: int
    chunk_index: int
    page_number: int | None
    text: str
    metadata: dict
    vector_score: float | None = None
    keyword_score: float | None = None
    bm25_score: float | None = None
    hybrid_score: float | None = None
    rerank_score: float | None = None
    final_rank: int | None = None


class RetrievalProvider(ABC):
    @abstractmethod
    def search(
        self,
        query_vector: list[float],
        contract_ids: list[int],
        top_k: int = 5,
        contract_id_filter: int | None = None,
    ) -> list[SearchResult]:
        """
        Perform semantic search over embedded chunks.

        Args:
            query_vector: Embedded representation of the user query.
            contract_ids: List of contract IDs the user is authorized to search.
            top_k: Number of top results to return.
            contract_id_filter: Optional single contract ID to narrow the search.

        Returns:
            List of SearchResult ordered by descending similarity score.
        """
        pass
