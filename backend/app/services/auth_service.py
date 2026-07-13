from typing import Dict, Optional

from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token, hash_password, verify_password
from app.schemas.auth import TokenResponse, UserResponse

STATIC_USERS: Dict[str, Dict] = {
    "admin": {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "System Administrator",
        "hashed_password": hash_password("admin123"),
    }
}


def authenticate_user(username: str, password: str) -> TokenResponse:
    user = STATIC_USERS.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        raise UnauthorizedException(detail="Invalid username or password")

    token = create_access_token(data={"sub": user["username"]})
    return TokenResponse(access_token=token)


def get_user_by_username(username: str) -> Optional[UserResponse]:
    user = STATIC_USERS.get(username)
    if not user:
        return None
    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        full_name=user["full_name"],
    )
