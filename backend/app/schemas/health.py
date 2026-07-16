from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class LLMHealthResponse(BaseModel):
    provider: str
    model: str
    configured: bool
