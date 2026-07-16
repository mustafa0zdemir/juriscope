from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage


class ChatMessageRepository:
    def create(
        self,
        db: Session,
        conversation_id: int,
        role: str,
        content: str,
        model: str | None = None,
        latency_ms: int | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            latency_ms=latency_ms,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    def list_by_conversation(self, db: Session, conversation_id: int) -> list[ChatMessage]:
        return list(
            db.execute(
                select(ChatMessage)
                .filter_by(conversation_id=conversation_id)
                .order_by(ChatMessage.created_at.asc())
            ).scalars().all()
        )

    def delete_all(self, db: Session, conversation_id: int) -> None:
        # Cascade delete is handled by database FK, but we can have this just in case.
        messages = self.list_by_conversation(db, conversation_id)
        for message in messages:
            db.delete(message)
        db.commit()
