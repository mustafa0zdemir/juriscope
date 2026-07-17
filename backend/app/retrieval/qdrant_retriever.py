import logging

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchAny, MatchValue

from app.config.settings import settings
from app.retrieval.base import RetrievalProvider, SearchResult

logger = logging.getLogger(__name__)


class QdrantRetriever(RetrievalProvider):
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection_name = settings.qdrant_collection

    def search(
        self,
        query_vector: list[float],
        contract_ids: list[int],
        top_k: int = 5,
        contract_id_filter: int | None = None,
    ) -> list[SearchResult]:
        if not contract_ids:
            return []

        # Build Qdrant payload filter
        if contract_id_filter is not None:
            # Single contract filter — already validated that it belongs to user
            payload_filter = Filter(
                must=[
                    FieldCondition(
                        key="contract_id",
                        match=MatchValue(value=contract_id_filter),
                    )
                ]
            )
        else:
            # All user contracts filter
            payload_filter = Filter(
                must=[
                    FieldCondition(
                        key="contract_id",
                        match=MatchAny(any=contract_ids),
                    )
                ]
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=payload_filter,
            limit=top_k,
            with_payload=True,
        )

        search_results = []
        for hit in results:
            payload = hit.payload or {}
            search_results.append(
                SearchResult(
                    score=hit.score,
                    chunk_id=payload.get("chunk_id", 0),
                    contract_id=payload.get("contract_id", 0),
                    chunk_index=payload.get("chunk_index", 0),
                    page_number=payload.get("page_number"),
                    text=payload.get("text", ""),
                    metadata={
                        k: v
                        for k, v in payload.items()
                        if k not in ("chunk_id", "contract_id", "chunk_index", "page_number", "text")
                    },
                    vector_score=hit.score,
                )
            )

        return search_results
