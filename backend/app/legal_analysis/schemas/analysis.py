from pydantic import BaseModel, Field

from app.legal_analysis.models.analysis import AnalysisType, RiskCategory, RiskSeverity


class LegalAnalysisRequest(BaseModel):
    analysis_type: AnalysisType = Field(default=AnalysisType.FULL)


class AnalysisCitation(BaseModel):
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


class RiskItem(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    severity: RiskSeverity
    reason: str = Field(min_length=1)
    citation: int | None = Field(default=None, ge=1)


class AnalysisFinding(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    citation: int | None = Field(default=None, ge=1)


class Recommendation(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    related_risk: str | None = Field(default=None, max_length=300)


class ParsedAnalysisResponse(BaseModel):
    summary: str = Field(min_length=1)
    risk_score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    risks: list[RiskItem]
    missing_clauses: list[AnalysisFinding]
    ambiguous_clauses: list[AnalysisFinding]
    one_sided_clauses: list[AnalysisFinding]
    recommendations: list[Recommendation]
    citations: list[int]


class LegalAnalysisResponse(BaseModel):
    analysis_type: AnalysisType
    summary: str
    risk_score: int = Field(ge=0, le=100)
    risk_category: RiskCategory
    confidence: float = Field(ge=0, le=1)
    risks: list[RiskItem]
    missing_clauses: list[AnalysisFinding]
    ambiguous_clauses: list[AnalysisFinding]
    one_sided_clauses: list[AnalysisFinding]
    recommendations: list[Recommendation]
    citations: list[AnalysisCitation]
