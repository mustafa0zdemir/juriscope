from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.legal_kb.services.legal_retriever import LegalRetriever
from app.reranking.rerank_service import ReRankService
from app.retrieval.base import SearchResult
from app.retrieval.hybrid_retriever import HybridSearchResult, RetrievalDebug
from app.services.retriever_service import RetrieverService


@dataclass(frozen=True)
class MultiSourceResults:
    contract_results: list[SearchResult]
    legal_results: list[SearchResult]
    results: list[SearchResult]


class MultiSourceRetrieverService:
    def __init__(
        self,
        contract_retriever: RetrieverService | None = None,
        legal_retriever: LegalRetriever | None = None,
        rerank_service: ReRankService | None = None,
    ) -> None:
        self.contract_retriever = contract_retriever or RetrieverService()
        self.legal_retriever = legal_retriever or LegalRetriever()
        self.rerank_service = rerank_service or ReRankService()

    def retrieve_with_debug(
        self,
        db: Session,
        question: str,
        user_id: int,
        contract_ids: list[int] | None = None,
        top_k: int = 5,
        search_mode: str = settings.default_search_mode,
        rerank: bool = True,
    ) -> HybridSearchResult:
        contract_result = self.contract_retriever.retrieve_with_debug(
            db=db,
            question=question,
            user_id=user_id,
            contract_ids=contract_ids,
            top_k=settings.rerank_input_limit if settings.enable_multi_source_rag else top_k,
            search_mode=search_mode,
            rerank=False if settings.enable_multi_source_rag else rerank,
        )
        if not settings.enable_multi_source_rag:
            return contract_result

        legal_results = self.legal_retriever.retrieve(
            db=db,
            question=question,
            top_k=settings.legal_top_k,
            rerank=False,
        )
        candidates = sorted(
            [*contract_result.results, *legal_results],
            key=lambda result: result.score,
            reverse=True,
        )[: settings.rerank_input_limit]
        if rerank and settings.rerank_enabled:
            results = self.rerank_service.rerank(question, candidates, top_k)
        else:
            results = candidates[:top_k]
        return HybridSearchResult(
            results=results,
            debug=RetrievalDebug(
                vector_hits=contract_result.debug.vector_hits,
                keyword_hits=contract_result.debug.keyword_hits,
                merged_hits=candidates,
                reranked_hits=results,
            ),
        )
