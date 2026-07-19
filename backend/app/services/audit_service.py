from sqlalchemy.orm import Session

from app.repositories.audit_log_repository import AuditLogRepository


class AuditService:
    @staticmethod
    def record(
        db: Session,
        event_type: str,
        outcome: str,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict | None = None,
    ) -> None:
        AuditLogRepository(db).create(
            event_type=event_type,
            outcome=outcome,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
