from enum import Enum

from pydantic import BaseModel, Field

from app.legal_analysis.schemas.analysis import AnalysisCitation, LegalAnalysisResponse


class ConfidenceLevel(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class AttributedSource(BaseModel):
    source_type: str
    title: str
    article: str | None = None
    page: int | None = None
    chunk: int
    similarity: float = Field(ge=0)
    rerank_score: float | None = None
    text_excerpt: str


class EvidenceItem(BaseModel):
    risk_title: str
    contract_chunk: AttributedSource | None = None
    law_chunk: AttributedSource | None = None
    case_law_chunk: AttributedSource | None = None
    similarity_score: float = Field(ge=0)
    rerank_score: float | None = None


class LegalReasoning(BaseModel):
    risk_title: str
    why_risky: str
    law_basis: str
    case_support: str
    affected_clause: str


class RetrievalPathStep(BaseModel):
    stage: str
    status: str
    detail: str
    hit_count: int | None = None


class ExplainableAnalysisResponse(BaseModel):
    analysis: LegalAnalysisResponse
    confidence_score: int = Field(ge=0, le=100)
    confidence_level: ConfidenceLevel
    reasoning: list[LegalReasoning]
    evidence: list[EvidenceItem]
    retrieval_path: list[RetrievalPathStep]
    matched_articles: list[AttributedSource]
    matched_cases: list[AttributedSource]
    used_contract_chunks: list[AttributedSource]
    citations: list[AnalysisCitation]
