from pydantic import BaseModel, Field

from app.config.settings import settings
from app.schemas.search import SearchDebugResponse, SearchMode, SearchResultItem
from app.trustworthy_rag.schemas import (
    CitationCoverage,
    GroundingResult,
    GuardrailReport,
    HallucinationRisk,
    RetrievalMetrics,
)


class ChatQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    contract_ids: list[int] | None = Field(default=None, min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    conversation_id: int | None = Field(default=None)
    search_mode: SearchMode = Field(default=SearchMode(settings.default_search_mode))
    rerank: bool = Field(default=True)



class CitationResponse(BaseModel):
    contract_id: int | None = None
    chunk_id: int
    chunk_index: int | None = None
    page_number: int | None = None
    score: float
    source_type: str = "contract"
    document_type: str | None = None
    title: str | None = None
    official_number: str | None = None
    article: str | None = None
    court: str | None = None
    decision_number: str | None = None
    publication_date: str | None = None
    page: int | None = None
    document_id: int | None = None


class PromptPreviewResponse(BaseModel):
    question: str
    retrieved_chunks: list[SearchResultItem]
    constructed_context: str
    constructed_prompt: str
    citations: list[CitationResponse]
    debug: SearchDebugResponse | None = None
    guardrails: GuardrailReport | None = None
    retrieval_metrics: RetrievalMetrics | None = None
    context_sufficient: bool = True


class ChatQueryResponse(BaseModel):
    conversation_id: int | None = None
    question: str
    answer: str
    citations: list[CitationResponse]
    used_chunks: list[SearchResultItem]
    model: str
    latency_ms: int
    debug: SearchDebugResponse | None = None
    guardrails: GuardrailReport | None = None
    grounding: GroundingResult | None = None
    citation_coverage: CitationCoverage | None = None
    hallucination_risk: HallucinationRisk | None = None
    retrieval_metrics: RetrievalMetrics | None = None
    context_sufficient: bool = True
    confidence: int | None = Field(default=None, ge=0, le=100)
