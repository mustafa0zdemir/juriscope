from dataclasses import replace

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.embeddings.sentence_transformer_provider import SentenceTransformerProvider
from app.legal_kb.models.legal_document import LegalDocumentType
from app.legal_kb.providers.legal_qdrant_retriever import LegalQdrantRetriever
from app.legal_kb.services.legal_bm25_service import LegalBM25Service
from app.reranking.rerank_service import ReRankService
from app.retrieval.base import SearchResult
from app.retrieval.hybrid_retriever import HybridRetriever


class LegalRetriever:
    def __init__(
        self,
        vector_retriever: LegalQdrantRetriever | None = None,
        bm25_service: LegalBM25Service | None = None,
        rerank_service: ReRankService | None = None,
    ) -> None:
        self.vector_retriever = vector_retriever or LegalQdrantRetriever()
        self.bm25_service = bm25_service or LegalBM25Service()
        self.rerank_service = rerank_service or ReRankService()

    def retrieve(
        self,
        db: Session,
        question: str,
        top_k: int | None = None,
        document_types: list[LegalDocumentType] | None = None,
        rerank: bool = True,
    ) -> list[SearchResult]:
        if not settings.enable_legal_search:
            return []

        requested_top_k = top_k or settings.legal_top_k
        candidate_limit = max(requested_top_k * 3, settings.rerank_input_limit)
        query_vector = SentenceTransformerProvider.get_instance().embed_text(question)
        vector_hits = self.vector_retriever.search(
            query_vector=query_vector,
            top_k=candidate_limit,
            document_types=document_types,
        )
        keyword_hits = self.bm25_service.search(
            db=db,
            question=question,
            top_k=candidate_limit,
            document_types=document_types,
        )
        merged = HybridRetriever.merge(vector_hits, keyword_hits)
        if rerank and settings.rerank_enabled:
            return self.rerank_service.rerank(
                question=question,
                chunks=merged[: settings.rerank_input_limit],
                top_n=min(requested_top_k, settings.legal_rerank_top_n),
            )
        return [replace(hit, final_rank=index) for index, hit in enumerate(merged[:requested_top_k], 1)]
