from enum import Enum

from pydantic import BaseModel, Field


class GroundingLevel(str, Enum):
    GROUNDED = "GROUNDED"
    PARTIALLY_GROUNDED = "PARTIALLY_GROUNDED"
    LOW_GROUNDED = "LOW_GROUNDED"


class HallucinationLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class GuardrailCheck(BaseModel):
    name: str
    passed: bool
    actual: float | int | str
    required: float | int | str
    message: str


class RetrievalMetrics(BaseModel):
    retrieved_chunks: int
    reranked_chunks: int
    used_chunks: int
    average_similarity: float = Field(ge=0)
    average_rerank_score: float = Field(ge=0)
    context_characters: int
    context_sources: list[str]
    search_mode: str


class GuardrailReport(BaseModel):
    enabled: bool
    passed: bool
    prompt_safe: bool
    checks: list[GuardrailCheck]
    warnings: list[str]


class CitationCoverage(BaseModel):
    total_claims: int
    supported_claims: int
    unsupported_claims: int
    coverage_percent: float = Field(ge=0, le=100)


class GroundingResult(BaseModel):
    level: GroundingLevel
    score: int = Field(ge=0, le=100)
    answer_empty: bool
    answer_too_short: bool
    has_citations: bool
    context_overlap: float = Field(ge=0, le=1)
    reasons: list[str]


class HallucinationRisk(BaseModel):
    score: int = Field(ge=0, le=100)
    level: HallucinationLevel
    factors: dict[str, float]


class InsufficientContextResponse(BaseModel):
    status: str = "insufficient_context"
    message: str
    confidence: int = 0
    context_sufficient: bool = False
    guardrails: GuardrailReport
    retrieval_metrics: RetrievalMetrics


class RAGDebugResponse(BaseModel):
    retrieval: dict
    rerank: dict
    context: str
    guardrails: GuardrailReport
    prompt: str
    grounding: GroundingResult | None
    citation_coverage: CitationCoverage | None
    hallucination_risk: HallucinationRisk | None
    llm_answer: str | None
    context_sufficient: bool
