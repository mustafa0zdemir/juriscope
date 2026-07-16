from fastapi import APIRouter, Depends
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
from app.schemas.search import SearchResultItem
from app.services.conversation_service import ConversationService
from app.services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["Chat"])


def _chunks_to_response(chunks) -> list[SearchResultItem]:
    return [
        SearchResultItem(
            score=chunk.score,
            chunk_id=chunk.chunk_id,
            contract_id=chunk.contract_id,
            chunk_index=chunk.chunk_index,
            page_number=chunk.page_number,
            text=chunk.text,
            metadata=chunk.metadata,
        )
        for chunk in chunks
    ]


def _citations_to_response(citations) -> list[CitationResponse]:
    return [CitationResponse.model_validate(citation.to_dict()) for citation in citations]


def _to_query_response(result, conversation_id: int | None = None) -> ChatQueryResponse:
    return ChatQueryResponse(
        conversation_id=conversation_id,
        question=result.question,
        answer=result.answer,
        citations=_citations_to_response(result.citations),
        used_chunks=_chunks_to_response(result.used_chunks),
        model=result.model,
        latency_ms=result.latency_ms,
    )


def _to_preview_response(result) -> PromptPreviewResponse:
    return PromptPreviewResponse(
        question=result.question,
        retrieved_chunks=_chunks_to_response(result.retrieved_chunks),
        constructed_context=result.constructed_context,
        constructed_prompt=result.constructed_prompt,
        citations=_citations_to_response(result.citations),
    )


@router.post("/query", response_model=ChatQueryResponse)
def chat_query(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation_service = ConversationService()
    
    if request.conversation_id:
        conversation = conversation_service.get_conversation(
            db=db, user_id=current_user.id, conversation_id=request.conversation_id
        )
    else:
        title = request.question[:250] + ("..." if len(request.question) > 250 else "")
        conversation = conversation_service.create_conversation(
            db=db, user_id=current_user.id, title=title
        )
        
    conversation_service.add_message(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation.id,
        role="user",
        content=request.question
    )

    result = RAGService().query(db=db, user_id=current_user.id, request=request)
    
    conversation_service.add_message(
        db=db,
        user_id=current_user.id,
        conversation_id=conversation.id,
        role="assistant",
        content=result.answer,
        model=result.model,
        latency_ms=result.latency_ms
    )
    
    return _to_query_response(result, conversation_id=conversation.id)


@router.post("/prompt-preview", response_model=PromptPreviewResponse)
def prompt_preview(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = RAGService().prepare_query(db=db, user_id=current_user.id, request=request)
    return _to_preview_response(result)
