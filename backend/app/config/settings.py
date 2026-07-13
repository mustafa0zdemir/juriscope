from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "Sozlesme Analizi Sistemi"
    app_version: str = "0.1.0"
    debug: bool = False

    secret_key: str = "change-this-to-a-secure-random-string"
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"

    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/sozlesme_db"

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 50

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()
