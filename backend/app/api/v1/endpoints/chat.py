import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatQueryRequest,
    ChatQueryResponse,
    CitationResponse,
    PromptPreviewResponse,
)
from app.config.settings import settings
from app.schemas.search import SearchResultItem
from app.services.conversation_service import ConversationService
from app.services.rag_service import RAGService
from app.trustworthy_rag.schemas import InsufficientContextResponse, RAGDebugResponse

router = APIRouter(prefix="/chat", tags=["Chat"])


def _chunks_to_response(chunks, include_debug: bool = False) -> list[SearchResultItem]:
    return [
        SearchResultItem(
            score=chunk.score,
            chunk_id=chunk.chunk_id,
            contract_id=chunk.contract_id,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
            text=chunk.text,
            metadata=chunk.metadata,
            vector_score=chunk.vector_score if include_debug else None,
            keyword_score=chunk.keyword_score if include_debug else None,
            bm25_score=chunk.bm25_score if include_debug else None,
            hybrid_score=chunk.hybrid_score if include_debug else None,
            rerank_score=chunk.rerank_score if include_debug else None,
            final_rank=chunk.final_rank if include_debug else None,
            source_type=chunk.source_type,
            document_id=chunk.document_id,
        )
        for chunk in chunks
    ]


def _citations_to_response(citations) -> list[CitationResponse]:
    return [CitationResponse.model_validate(citation.to_dict()) for citation in citations]


def _debug_to_response(debug):
    if debug is None:
        return None
    from app.schemas.search import SearchDebugResponse

    return SearchDebugResponse(
        vector_hits=_chunks_to_response(debug.vector_hits, include_debug=True),
        keyword_hits=_chunks_to_response(debug.keyword_hits, include_debug=True),
        merged_hits=_chunks_to_response(debug.merged_hits, include_debug=True),
        reranked_hits=_chunks_to_response(debug.reranked_hits, include_debug=True),
    )


def _to_query_response(result, conversation_id: int | None = None) -> ChatQueryResponse:
    return ChatQueryResponse(
        conversation_id=conversation_id,
        question=result.question,
        answer=result.answer,
        citations=_citations_to_response(result.citations),
        used_chunks=_chunks_to_response(result.used_chunks, include_debug=settings.enable_debug_search),
        model=result.model,
        latency_ms=result.latency_ms,
        debug=_debug_to_response(getattr(result, "retrieval_debug", None)),
        guardrails=getattr(result, "guardrails", None),
        grounding=getattr(result, "grounding", None),
        citation_coverage=getattr(result, "citation_coverage", None),
        hallucination_risk=getattr(result, "hallucination_risk", None),
        retrieval_metrics=getattr(result, "retrieval_metrics", None),
        context_sufficient=getattr(result, "context_sufficient", True),
        confidence=getattr(result, "confidence", None),
    )


def _to_preview_response(result) -> PromptPreviewResponse:
    return PromptPreviewResponse(
        question=result.question,
        retrieved_chunks=_chunks_to_response(result.retrieved_chunks, include_debug=settings.enable_debug_search),
        constructed_context=result.constructed_context,
        constructed_prompt=result.constructed_prompt,
        citations=_citations_to_response(result.citations),
        debug=_debug_to_response(getattr(result, "retrieval_debug", None)),
        guardrails=getattr(result, "guardrails", None),
        retrieval_metrics=getattr(result, "retrieval_metrics", None),
        context_sufficient=getattr(result, "context_sufficient", True),
    )


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_or_create_conversation(db, user_id: int, conversation_id: int | None, question: str):
    conversation_service = ConversationService()
    if conversation_id:
        conversation = conversation_service.get_conversation(
            db=db, user_id=user_id, conversation_id=conversation_id
        )
    else:
        title = question[:250] + ("..." if len(question) > 250 else "")
        conversation = conversation_service.create_conversation(
            db=db, user_id=user_id, title=title
        )
    conversation_service.add_message(
        db=db,
        user_id=user_id,
        conversation_id=conversation.id,
        role="user",
        content=question,
    )
    return conversation


@router.post("/query", response_model=ChatQueryResponse | InsufficientContextResponse)
def chat_query(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = _get_or_create_conversation(
        db, current_user.id, request.conversation_id, request.question
    )
    conversation_service = ConversationService()

    result = RAGService().query(db=db, user_id=current_user.id, request=request)
    if isinstance(result, InsufficientContextResponse):
        return result
    
    conversation_service.add_message(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation.id,
        role="assistant",
        content=result.answer,
        model=result.model,
        latency_ms=result.latency_ms,
        citations=[citation.to_dict() for citation in result.citations],
    )
    
    return _to_query_response(result, conversation_id=conversation.id)


@router.post("/debug", response_model=RAGDebugResponse)
def chat_debug(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not settings.enable_debug_chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat debug endpoint kapalı")
    return RAGService().debug_query(db=db, user_id=current_user.id, request=request)


@router.post("/stream")
def chat_stream(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = _get_or_create_conversation(
        db, current_user.id, request.conversation_id, request.question
    )
    events = RAGService().stream_query(
        db=db,
        user_id=current_user.id,
        request=request,
        conversation_id=conversation.id,
    )

    def event_stream():
        for event in events:
            yield _format_sse(event.event, event.data)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/prompt-preview", response_model=PromptPreviewResponse)
def prompt_preview(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = RAGService().prepare_query(db=db, user_id=current_user.id, request=request)
    return _to_preview_response(result)
