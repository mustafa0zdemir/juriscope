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

    database_url: str = "postgresql+psycopg2://postgres:postgres@postgres:5432/contract_analysis"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "contracts"
    minio_secure: bool = False

    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "contracts"
    embedding_model: str = "BAAI/bge-m3"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    max_output_tokens: int = 1024
    temperature: float = 0.2
    top_p: float = 0.95
    gemini_timeout_seconds: float = 30.0

    default_search_mode: str = "hybrid"
    enable_debug_search: bool = False

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20
    allowed_extensions: list[str] = [".pdf", ".doc", ".docx"]

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()
