from fastapi import APIRouter

from app.config.settings import settings
from app.core.rate_limit import auth_rate_limiter
from app.llm.gemini_provider import GeminiProvider
from app.schemas.health import (
    CacheHealthResponse,
    HealthResponse,
    LLMHealthResponse,
    RAGHealthResponse,
)

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()


@router.get("/health/llm", response_model=LLMHealthResponse)
async def llm_health_check():
    return LLMHealthResponse(
        provider="gemini",
        model=settings.gemini_model,
        configured=GeminiProvider.is_configured(),
    )


@router.get("/health/cache", response_model=CacheHealthResponse)
def cache_health_check():
    return CacheHealthResponse(
        enabled=settings.redis_enabled,
        status=auth_rate_limiter.status(),
    )


@router.get("/health/rag", response_model=RAGHealthResponse)
async def rag_health_check():
    llm_status = "configured" if GeminiProvider.is_configured() else "not_configured"
    return RAGHealthResponse(
        retrieval="available",
        reranker="enabled" if settings.rerank_enabled else "disabled",
        guardrails="enabled" if settings.enable_rag_guardrails else "disabled",
        llm=llm_status,
        legal_search="enabled" if settings.enable_legal_search else "disabled",
        status="ok" if llm_status == "configured" else "degraded",
    )
