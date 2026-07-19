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
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"
    password_min_length: int = 12
    max_login_attempts: int = 5
    login_lock_minutes: int = 15
    auth_rate_limit_requests: int = 10
    auth_rate_limit_window_seconds: int = 60

    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
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
    legal_collection: str = "legal_documents"
    embedding_model: str = "BAAI/bge-m3"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_analysis_model: str = "gemini-3.1-flash-lite"
    max_output_tokens: int = 1024
    temperature: float = 0.2
    top_p: float = 0.95
    gemini_timeout_seconds: float = 30.0
    analysis_top_k: int = 6
    analysis_rerank_enabled: bool = False
    analysis_max_output_tokens: int = 3072

    default_search_mode: str = "hybrid"
    enable_debug_search: bool = False
    rerank_enabled: bool = True
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    rerank_input_limit: int = 20
    rerank_top_n: int = 5
    rerank_timeout_seconds: float = 30.0
    enable_legal_search: bool = True
    enable_multi_source_rag: bool = True
    legal_top_k: int = 10
    legal_rerank_top_n: int = 5

    enable_rag_guardrails: bool = True
    enable_grounding_check: bool = True
    enable_citation_validation: bool = True
    enable_hallucination_check: bool = True
    min_context_chunks: int = 1
    min_context_characters: int = 10
    min_retrieval_score: float = 0.2
    min_rerank_score: float = 0.0
    enable_debug_chat: bool = False

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
