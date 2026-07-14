from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse, UserResponse


def authenticate_user(db: Session, username: str, password: str) -> TokenResponse:
    repo = UserRepository(db)
    user = repo.get_by_username(username)

    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedException(detail="Invalid username or password")

    if not user.is_active:
        raise UnauthorizedException(detail="Account is inactive")

    token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=token)


def get_user_by_username(db: Session, username: str) -> Optional[UserResponse]:
    repo = UserRepository(db)
    user = repo.get_by_username(username)
    if not user:
        return None
    return UserResponse.model_validate(user)
