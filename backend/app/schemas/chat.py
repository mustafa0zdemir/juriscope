from pydantic import BaseModel, Field

from app.schemas.search import SearchResultItem


class ChatQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    contract_ids: list[int] | None = Field(default=None, min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


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


class ChatQueryResponse(BaseModel):
    question: str
    answer: str
    citations: list[CitationResponse]
    used_chunks: list[SearchResultItem]
    model: str
    latency_ms: int
