from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from jwt.exceptions import InvalidTokenError

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import BadRequestException, ConflictException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User
from app.models.user_session import UserSession
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.schemas.auth import RegisterRequest, RegisterResponse, SessionResponse, TokenResponse, UserResponse
from app.services.audit_service import AuditService


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _issue_token_pair(
    db: Session,
    user: User,
    ip_address: str | None,
    user_agent: str | None,
) -> TokenResponse:
    session_id = str(uuid4())
    refresh_token = create_refresh_token(user.id, session_id)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "type": "access",
            "sid": session_id,
        }
    )
    UserSessionRepository(db).create(
        UserSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=_utc_now() + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def register_user(
    db: Session,
    request: RegisterRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> RegisterResponse:
    repo = UserRepository(db)
    if repo.get_by_username(request.username):
        raise ConflictException(detail="Bu kullanıcı adı zaten kullanılıyor")
    if repo.get_by_email(request.email):
        raise ConflictException(detail="Bu e-posta adresi zaten kullanılıyor")

    user = repo.create(
        username=request.username,
        email=request.email,
        full_name=request.full_name,
        hashed_password=hash_password(request.password),
    )
    AuditService.record(
        db,
        event_type="auth.register",
        outcome="success",
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return RegisterResponse(
        message="Hesabınız başarıyla oluşturuldu",
        user=UserResponse.model_validate(user),
    )


def authenticate_user(
    db: Session,
    username: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TokenResponse:
    repo = UserRepository(db)
    user = repo.get_by_username_or_email(username)

    if user and user.locked_until:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if user.locked_until > now:
            raise UnauthorizedException(detail="Hesap geçici olarak kilitlendi. Lütfen daha sonra tekrar deneyin")
        repo.update(user, failed_login_attempts=0, locked_until=None)

    if not user or not verify_password(password, user.hashed_password):
        if user:
            failed_attempts = user.failed_login_attempts + 1
            updates: dict[str, object] = {"failed_login_attempts": failed_attempts}
            if failed_attempts >= settings.max_login_attempts:
                updates["locked_until"] = (
                    datetime.now(timezone.utc).replace(tzinfo=None)
                    + timedelta(minutes=settings.login_lock_minutes)
                )
            repo.update(user, **updates)
        AuditService.record(
            db,
            event_type="auth.login",
            outcome="failure",
            user_id=user.id if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"identifier": username.strip().lower()},
        )
        raise UnauthorizedException(detail="Kullanıcı adı/e-posta veya şifre hatalı")

    if not user.is_active:
        raise UnauthorizedException(detail="Hesap kullanıma kapalı")

    if user.failed_login_attempts or user.locked_until:
        repo.update(user, failed_login_attempts=0, locked_until=None)

    tokens = _issue_token_pair(db, user, ip_address, user_agent)
    AuditService.record(
        db,
        event_type="auth.login",
        outcome="success",
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return tokens


def refresh_session(
    db: Session,
    refresh_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TokenResponse:
    try:
        payload = decode_access_token(refresh_token)
    except InvalidTokenError as exc:
        raise UnauthorizedException(detail="Geçersiz veya süresi dolmuş yenileme anahtarı") from exc
    if payload.get("type") != "refresh" or not payload.get("jti") or not payload.get("sub"):
        raise UnauthorizedException(detail="Geçersiz yenileme anahtarı")

    session_repo = UserSessionRepository(db)
    session = session_repo.get(payload["jti"])
    if (
        not session
        or session.revoked_at is not None
        or session.expires_at <= _utc_now()
        or session.refresh_token_hash != hash_token(refresh_token)
    ):
        if session:
            session_repo.revoke(session)
        raise UnauthorizedException(detail="Oturum geçersiz veya sonlandırılmış")

    user = UserRepository(db).get_by_id(int(payload["sub"]))
    if not user or not user.is_active:
        raise UnauthorizedException(detail="Kullanıcı hesabı kullanılamıyor")

    session_repo.revoke(session)
    tokens = _issue_token_pair(db, user, ip_address, user_agent)
    AuditService.record(
        db,
        event_type="auth.refresh",
        outcome="success",
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return tokens


def logout_session(db: Session, user_id: int, refresh_token: str) -> None:
    try:
        payload = decode_access_token(refresh_token)
    except InvalidTokenError:
        return
    session_id = payload.get("jti")
    if payload.get("type") != "refresh" or not session_id:
        return
    session = UserSessionRepository(db).get(session_id)
    if session and session.user_id == user_id and session.revoked_at is None:
        UserSessionRepository(db).revoke(session)
    AuditService.record(db, "auth.logout", "success", user_id=user_id)


def list_active_sessions(db: Session, user_id: int) -> list[SessionResponse]:
    return [SessionResponse.model_validate(item) for item in UserSessionRepository(db).list_active(user_id)]


def revoke_session(db: Session, user_id: int, session_id: str) -> None:
    repo = UserSessionRepository(db)
    session = repo.get(session_id)
    if not session or session.user_id != user_id:
        raise BadRequestException(detail="Oturum bulunamadı")
    if session.revoked_at is None:
        repo.revoke(session)
    AuditService.record(db, "auth.session_revoke", "success", user_id=user_id)


def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> None:
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user or not verify_password(current_password, user.hashed_password):
        raise BadRequestException(detail="Mevcut şifre hatalı")
    if verify_password(new_password, user.hashed_password):
        raise BadRequestException(detail="Yeni şifre mevcut şifreyle aynı olamaz")
    user_repo.update(
        user,
        hashed_password=hash_password(new_password),
        password_changed_at=_utc_now(),
        failed_login_attempts=0,
        locked_until=None,
    )
    UserSessionRepository(db).revoke_all(user_id)
    AuditService.record(db, "auth.password_change", "success", user_id=user_id)


def get_user_by_username(db: Session, username: str) -> Optional[UserResponse]:
    repo = UserRepository(db)
    user = repo.get_by_username(username)
    if not user:
        return None
    return UserResponse.model_validate(user)
