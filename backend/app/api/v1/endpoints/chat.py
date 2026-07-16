from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse, CitationResponse
from app.schemas.search import SearchResultItem
from app.services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["Chat"])


def _to_response(result) -> ChatQueryResponse:
    return ChatQueryResponse(
        question=result.question,
        retrieved_chunks=[
            SearchResultItem(
                score=chunk.score,
                chunk_id=chunk.chunk_id,
                contract_id=chunk.contract_id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                text=chunk.text,
                metadata=chunk.metadata,
            )
            for chunk in result.retrieved_chunks
        ],
        constructed_context=result.constructed_context,
        constructed_prompt=result.constructed_prompt,
        citations=[CitationResponse.model_validate(citation.to_dict()) for citation in result.citations],
    )


@router.post("/query", response_model=ChatQueryResponse)
def chat_query(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = RAGService().prepare_query(db=db, user_id=current_user.id, request=request)
    return _to_response(result)


@router.post("/prompt-preview", response_model=ChatQueryResponse)
def prompt_preview(
    request: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = RAGService().prepare_query(db=db, user_id=current_user.id, request=request)
    return _to_response(result)
