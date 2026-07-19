from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, RegisterResponse, TokenResponse, UserResponse


def register_user(db: Session, request: RegisterRequest) -> RegisterResponse:
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
    return RegisterResponse(
        message="Hesabınız başarıyla oluşturuldu",
        user=UserResponse.model_validate(user),
    )


def authenticate_user(db: Session, username: str, password: str) -> TokenResponse:
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
        raise UnauthorizedException(detail="Kullanıcı adı/e-posta veya şifre hatalı")

    if not user.is_active:
        raise UnauthorizedException(detail="Hesap kullanıma kapalı")

    if user.failed_login_attempts or user.locked_until:
        repo.update(user, failed_login_attempts=0, locked_until=None)

    token = create_access_token(data={"sub": str(user.id), "username": user.username, "type": "access"})
    return TokenResponse(access_token=token)


def get_user_by_username(db: Session, username: str) -> Optional[UserResponse]:
    repo = UserRepository(db)
    user = repo.get_by_username(username)
    if not user:
        return None
    return UserResponse.model_validate(user)
