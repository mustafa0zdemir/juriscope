from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user_session import UserSession


class UserSessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, session: UserSession) -> UserSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get(self, session_id: str) -> UserSession | None:
        return self.db.get(UserSession, session_id)

    def list_active(self, user_id: int) -> list[UserSession]:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return (
            self.db.query(UserSession)
            .filter(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
            )
            .order_by(UserSession.last_used_at.desc())
            .all()
        )

    def revoke(self, session: UserSession) -> None:
        session.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()

    def revoke_all(self, user_id: int) -> int:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        count = (
            self.db.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .update({"revoked_at": now}, synchronize_session=False)
        )
        self.db.commit()
        return count
