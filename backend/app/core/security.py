from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import re

import jwt
from passlib.context import CryptContext

from app.config.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> list[str]:
    errors: list[str] = []
    if len(password) < settings.password_min_length:
        errors.append(f"Şifre en az {settings.password_min_length} karakter olmalıdır")
    if not re.search(r"[a-zçğıöşü]", password):
        errors.append("Şifre en az bir küçük harf içermelidir")
    if not re.search(r"[A-ZÇĞİÖŞÜ]", password):
        errors.append("Şifre en az bir büyük harf içermelidir")
    if not re.search(r"\d", password):
        errors.append("Şifre en az bir rakam içermelidir")
    if not re.search(r"[^\w\s]", password, flags=re.UNICODE):
        errors.append("Şifre en az bir özel karakter içermelidir")
    return errors


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
