from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError

from app.core.exceptions import UnauthorizedException
from app.core.security import decode_access_token
from app.schemas.auth import UserResponse
from app.services.auth_service import get_user_by_username

security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> UserResponse:
    try:
        payload = decode_access_token(credentials.credentials)
        username: str = payload.get("sub")
        if username is None:
            raise UnauthorizedException(detail="Invalid token payload")
    except InvalidTokenError:
        raise UnauthorizedException(detail="Invalid or expired token")

    user = get_user_by_username(username)
    if user is None:
        raise UnauthorizedException(detail="User not found")

    return user
