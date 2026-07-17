from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation


class ConversationRepository:
    def create(self, db: Session, user_id: int, title: str) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    def get(self, db: Session, conversation_id: int) -> Conversation | None:
        return db.execute(select(Conversation).filter_by(id=conversation_id)).scalar_one_or_none()

    def list_by_user(self, db: Session, user_id: int) -> list[Conversation]:
        return list(
            db.execute(
                select(Conversation)
                .filter_by(user_id=user_id)
                .order_by(Conversation.updated_at.desc())
            ).scalars().all()
        )

    def update_title(self, db: Session, conversation_id: int, title: str) -> Conversation | None:
        conversation = self.get(db, conversation_id)
        if conversation:
            conversation.title = title
            db.commit()
            db.refresh(conversation)
        return conversation

    def delete(self, db: Session, conversation_id: int) -> bool:
        conversation = self.get(db, conversation_id)
        if conversation:
            db.delete(conversation)
            db.commit()
            return True
        return False

    def touch(self, db: Session, conversation_id: int) -> None:
        conversation = self.get(db, conversation_id)
        if conversation:
            conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
