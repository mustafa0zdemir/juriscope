from pydantic import BaseModel, Field

from app.config.settings import settings
from app.schemas.search import SearchDebugResponse, SearchMode, SearchResultItem


class ChatQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    contract_ids: list[int] | None = Field(default=None, min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    conversation_id: int | None = Field(default=None)
    search_mode: SearchMode = Field(default=SearchMode(settings.default_search_mode))
    rerank: bool = Field(default=True)



class CitationResponse(BaseModel):
    contract_id: int
    chunk_id: int
    chunk_index: int
    page_number: int | None
    score: float


class PromptPreviewResponse(BaseModel):
    question: str
    retrieved_chunks: list[SearchResultItem]
    constructed_context: str
    constructed_prompt: str
    citations: list[CitationResponse]
    debug: SearchDebugResponse | None = None


class ChatQueryResponse(BaseModel):
    conversation_id: int | None = None
    question: str
    answer: str
    citations: list[CitationResponse]
    used_chunks: list[SearchResultItem]
    model: str
    latency_ms: int
    debug: SearchDebugResponse | None = None
