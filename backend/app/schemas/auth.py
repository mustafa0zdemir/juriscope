import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config.settings import settings
from app.core.security import validate_password_strength


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=255)
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=settings.password_min_length, max_length=128)
    password_confirmation: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9._-]+", normalized):
            raise ValueError("Kullanıcı adı yalnızca harf, rakam, nokta, tire ve alt çizgi içerebilir")
        return normalized

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
            raise ValueError("Geçerli bir e-posta adresi girilmelidir")
        return normalized

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def validate_password(self) -> "RegisterRequest":
        if self.password != self.password_confirmation:
            raise ValueError("Şifreler eşleşmiyor")
        errors = validate_password_strength(self.password)
        if errors:
            raise ValueError("; ".join(errors))
        return self


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: str | None = None
    is_active: bool
    is_admin: bool
    email_verified: bool = False


class RegisterResponse(BaseModel):
    message: str
    user: UserResponse
