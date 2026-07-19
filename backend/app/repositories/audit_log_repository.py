from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        event_type: str,
        outcome: str,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            event_type=event_type,
            outcome=outcome,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry
