from enum import Enum

from pydantic import BaseModel, Field


class ClauseType(str, Enum):
    CONFIDENTIALITY = "CONFIDENTIALITY"
    TERMINATION = "TERMINATION"
    PENALTY = "PENALTY"
    FORCE_MAJEURE = "FORCE_MAJEURE"
    ARBITRATION = "ARBITRATION"
    JURISDICTION = "JURISDICTION"
    PAYMENT = "PAYMENT"
    DURATION = "DURATION"
    DELIVERY = "DELIVERY"
    KVKK = "KVKK"
    NON_COMPETE = "NON_COMPETE"
    INTELLECTUAL_PROPERTY = "INTELLECTUAL_PROPERTY"


class RiskTag(str, Enum):
    FINANCIAL = "Financial"
    LEGAL = "Legal"
    PRIVACY = "Privacy"
    COMMERCIAL = "Commercial"
    EMPLOYMENT = "Employment"


class DetectedClause(BaseModel):
    clause_type: ClauseType
    title: str
    contract_id: int
    chunk_id: int
    chunk_index: int
    page_number: int | None = None
    text: str
    confidence: float = Field(ge=0, le=1)
    matched_keywords: list[str]
    risk_tags: list[RiskTag]


class ClauseListResponse(BaseModel):
    contract_id: int
    clauses: list[DetectedClause]
    detected_types: list[ClauseType]
    missing_types: list[ClauseType]


class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    PARTIAL = "PARTIAL"
    NON_COMPLIANT = "NON_COMPLIANT"


class ComplianceFinding(BaseModel):
    law: str
    status: ComplianceStatus
    required_clauses: list[ClauseType]
    detected_clauses: list[ClauseType]
    missing_clauses: list[ClauseType]
    issues: list[str]
    recommendation: str


class ComplianceReport(BaseModel):
    contract_id: int
    compliance_score: int = Field(ge=0, le=100)
    status: ComplianceStatus
    findings: list[ComplianceFinding]
    risk_tags: list[RiskTag]
    disclaimer: str


class ContractComparisonRequest(BaseModel):
    base_contract_id: int
    comparison_contract_id: int


class ClauseChange(BaseModel):
    clause_type: ClauseType
    before: DetectedClause | None = None
    after: DetectedClause | None = None
    similarity: float = Field(ge=0, le=1)
    summary: str


class RiskChange(BaseModel):
    clause_type: ClauseType
    before_tags: list[RiskTag]
    after_tags: list[RiskTag]
    direction: str


class ContractComparisonResponse(BaseModel):
    base_contract_id: int
    comparison_contract_id: int
    added_clauses: list[DetectedClause]
    removed_clauses: list[DetectedClause]
    modified_clauses: list[ClauseChange]
    unchanged_clauses: list[ClauseType]
    risk_changes: list[RiskChange]
    new_obligations: list[str]
    new_rights: list[str]
    summary: str
