from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedException
from app.core.security import decode_access_token
from app.dependencies.database import get_db
from app.schemas.auth import UserResponse
from app.services.auth_service import get_user_by_username

security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        payload = decode_access_token(credentials.credentials)
        username: str = payload.get("sub")
        if username is None:
            raise UnauthorizedException(detail="Invalid token payload")
    except InvalidTokenError:
        raise UnauthorizedException(detail="Invalid or expired token")

    user = get_user_by_username(db, username)
    if user is None:
        raise UnauthorizedException(detail="User not found")

    return user
