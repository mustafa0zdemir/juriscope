from fastapi import APIRouter

from app.config.settings import settings
from app.llm.gemini_provider import GeminiProvider
from app.schemas.health import HealthResponse, LLMHealthResponse

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
