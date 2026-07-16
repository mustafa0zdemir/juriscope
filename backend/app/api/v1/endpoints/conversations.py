from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.conversation import (
    ChatMessageResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    request: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ConversationService()
    conversation = service.create_conversation(
        db=db, user_id=current_user.id, title=request.title
    )
    return conversation


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ConversationService()
    return service.list_user_conversations(db=db, user_id=current_user.id)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ConversationService()
    return service.get_conversation(
        db=db, user_id=current_user.id, conversation_id=conversation_id
    )


@router.get("/{conversation_id}/messages", response_model=list[ChatMessageResponse])
def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ConversationService()
    return service.get_messages(
        db=db, user_id=current_user.id, conversation_id=conversation_id
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ConversationService()
    service.delete_conversation(
        db=db, user_id=current_user.id, conversation_id=conversation_id
    )
