from qdrant_client import QdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchAny

from app.config.settings import settings
from app.legal_kb.models.legal_document import LegalDocumentType
from app.retrieval.base import SearchResult


class LegalQdrantRetriever:
    def __init__(self, client: QdrantClient | None = None) -> None:
        self.client = client or QdrantClient(url=settings.qdrant_url)
        self.collection_name = settings.legal_collection

    def search(
        self,
        query_vector: list[float],
        top_k: int,
        document_types: list[LegalDocumentType] | None = None,
    ) -> list[SearchResult]:
        query_filter = None
        if document_types:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_type",
                        match=MatchAny(any=[document_type.value for document_type in document_types]),
                    )
                ]
            )

        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
        return [self._to_result(hit) for hit in hits]

    @staticmethod
    def _to_result(hit) -> SearchResult:
        payload = hit.payload or {}
        return SearchResult(
            score=hit.score,
            chunk_id=payload.get("chunk_id", 0),
            contract_id=None,
            chunk_index=payload.get("chunk_index", 0),
            page_number=payload.get("page_number"),
            text=payload.get("text", ""),
            metadata=payload,
            vector_score=hit.score,
            source_type="legal",
            document_id=payload.get("document_id"),
        )
