from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage
from app.models.conversation import Conversation
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.conversation_repository import ConversationRepository


class ConversationService:
    def __init__(
        self,
        conversation_repo: ConversationRepository | None = None,
        chat_message_repo: ChatMessageRepository | None = None,
    ):
        self.conversation_repo = conversation_repo or ConversationRepository()
        self.chat_message_repo = chat_message_repo or ChatMessageRepository()

    def get_conversation_or_404(self, db: Session, conversation_id: int) -> Conversation:
        conversation = self.conversation_repo.get(db, conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        return conversation

    def check_user_access(self, conversation: Conversation, user_id: int) -> None:
        if conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this conversation"
            )

    def create_conversation(self, db: Session, user_id: int, title: str) -> Conversation:
        return self.conversation_repo.create(db=db, user_id=user_id, title=title)

    def get_conversation(self, db: Session, user_id: int, conversation_id: int) -> Conversation:
        conversation = self.get_conversation_or_404(db, conversation_id)
        self.check_user_access(conversation, user_id)
        return conversation

    def list_user_conversations(self, db: Session, user_id: int) -> list[Conversation]:
        return self.conversation_repo.list_by_user(db, user_id)

    def delete_conversation(self, db: Session, user_id: int, conversation_id: int) -> None:
        conversation = self.get_conversation_or_404(db, conversation_id)
        self.check_user_access(conversation, user_id)
        self.conversation_repo.delete(db, conversation_id)

    def add_message(
        self,
        db: Session,
        user_id: int,
        conversation_id: int,
        role: str,
        content: str,
        model: str | None = None,
        latency_ms: int | None = None,
        citations: list[dict] | None = None,
    ) -> ChatMessage:
        conversation = self.get_conversation_or_404(db, conversation_id)
        self.check_user_access(conversation, user_id)
        if role == "user" and conversation.title == "Yeni Sohbet":
            conversation.title = content[:250] + ("..." if len(content) > 250 else "")
        message = self.chat_message_repo.create(
            db=db,
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            latency_ms=latency_ms,
            citations=citations,
        )
        self.conversation_repo.touch(db, conversation_id)
        return message

    def get_messages(self, db: Session, user_id: int, conversation_id: int) -> list[ChatMessage]:
        conversation = self.get_conversation_or_404(db, conversation_id)
        self.check_user_access(conversation, user_id)
        return self.chat_message_repo.list_by_conversation(db, conversation_id)
