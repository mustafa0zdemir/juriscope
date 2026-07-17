from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class LLMHealthResponse(BaseModel):
    provider: str
    model: str
    configured: bool


class RAGHealthResponse(BaseModel):
    retrieval: str
    reranker: str
    guardrails: str
    llm: str
    legal_search: str
    status: str
