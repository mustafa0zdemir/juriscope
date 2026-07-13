from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import authenticate_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    return authenticate_user(request.username, request.password)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user
