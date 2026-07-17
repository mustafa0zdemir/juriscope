from sqlalchemy.orm import Session

from app.config.settings import settings
from app.retrieval.base import SearchResult
from app.schemas.search import SearchDebugResponse, SearchRequest, SearchResponse, SearchResultItem
from app.services.retriever_service import RetrieverService


def _to_result_item(result: SearchResult, include_debug: bool = False) -> SearchResultItem:
    return SearchResultItem(
        score=result.score,
        chunk_id=result.chunk_id,
        contract_id=result.contract_id,
        chunk_index=result.chunk_index,
        page_number=result.page_number,
        text=result.text,
        metadata=result.metadata,
        vector_score=result.vector_score if include_debug else None,
        keyword_score=result.keyword_score if include_debug else None,
        bm25_score=result.bm25_score if include_debug else None,
        hybrid_score=result.hybrid_score if include_debug else None,
        rerank_score=result.rerank_score if include_debug else None,
        final_rank=result.final_rank if include_debug else None,
        source_type=result.source_type,
        document_id=result.document_id,
    )


def semantic_search(
    db: Session,
    request: SearchRequest,
    user_id: int,
) -> SearchResponse:
    retrieval_result = RetrieverService().retrieve_with_debug(
        db=db,
        question=request.query,
        user_id=user_id,
        contract_ids=[request.contract_id] if request.contract_id is not None else None,
        top_k=request.top_k,
        search_mode=request.search_mode.value,
        rerank=request.rerank,
    )

    debug = None
    if settings.enable_debug_search:
        debug = SearchDebugResponse(
            vector_hits=[_to_result_item(hit, include_debug=True) for hit in retrieval_result.debug.vector_hits],
            keyword_hits=[_to_result_item(hit, include_debug=True) for hit in retrieval_result.debug.keyword_hits],
            merged_hits=[_to_result_item(hit, include_debug=True) for hit in retrieval_result.debug.merged_hits],
            reranked_hits=[_to_result_item(hit, include_debug=True) for hit in retrieval_result.debug.reranked_hits],
        )

    return SearchResponse(
        query=request.query,
        results=[_to_result_item(hit, include_debug=settings.enable_debug_search) for hit in retrieval_result.results],
        total=len(retrieval_result.results),
        debug=debug,
    )
