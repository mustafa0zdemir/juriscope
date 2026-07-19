from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token
from app.dependencies.database import get_db
from app.schemas.auth import UserResponse
from app.repositories.user_repository import UserRepository

security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        payload = decode_access_token(credentials.credentials)
        subject: str | None = payload.get("sub")
        if subject is None or payload.get("type", "access") != "access":
            raise UnauthorizedException(detail="Invalid token payload")
    except InvalidTokenError:
        raise UnauthorizedException(detail="Invalid or expired token")

    repo = UserRepository(db)
    user = repo.get_by_id(int(subject)) if subject.isdigit() else repo.get_by_username(subject)
    if user is None:
        raise UnauthorizedException(detail="User not found")

    return UserResponse.model_validate(user)


def require_admin(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    if not current_user.is_admin:
        raise ForbiddenException(detail="Bu işlem için yönetici yetkisi gerekiyor")
    return current_user
