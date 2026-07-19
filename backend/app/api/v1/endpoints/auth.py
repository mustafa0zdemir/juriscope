from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.rate_limit import enforce_auth_rate_limit
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    SessionResponse,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    change_password,
    list_active_sessions,
    logout_session,
    refresh_session,
    register_user,
    revoke_session,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
):
    return authenticate_user(
        db,
        payload.username,
        payload.password,
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
):
    return register_user(
        db,
        payload,
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
):
    return refresh_session(
        db,
        payload.refresh_token,
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: RefreshTokenRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logout_session(db, current_user.id, payload.refresh_token)
    return MessageResponse(message="Oturum güvenli biçimde sonlandırıldı")


@router.post("/change-password", response_model=MessageResponse)
def update_password(
    payload: ChangePasswordRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    change_password(db, current_user.id, payload.current_password, payload.new_password)
    return MessageResponse(message="Şifreniz değiştirildi. Tüm oturumlar sonlandırıldı")


@router.get("/sessions", response_model=list[SessionResponse])
def sessions(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_active_sessions(db, current_user.id)


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
def delete_session(
    session_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revoke_session(db, current_user.id, session_id)
    return MessageResponse(message="Oturum sonlandırıldı")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user
