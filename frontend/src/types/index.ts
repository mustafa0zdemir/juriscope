export interface LoginCredentials {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  is_admin: boolean;
}

export interface UploadResponse {
  filename: string;
  size: number;
  content_type: string;
  message: string;
}

export interface Contract {
  id: number;
  user_id: number;
  original_filename: string;
  stored_filename: string;
  storage_key: string;
  mime_type: string;
  file_size: number;
  status: string;
  uploaded_at: string;
  updated_at: string;
}

export interface ContractListResponse {
  items: Contract[];
  total: number;
}

export interface Citation {
  contract_id?: number | null;
  chunk_id: number;
  chunk_index?: number | null;
  page_number?: number | null;
  score: number;
  source_type?: "contract" | "legal";
  document_id?: number | null;
  document_type?: LegalDocumentType | null;
  title?: string | null;
  official_number?: string | null;
  article?: string | null;
  court?: string | null;
  decision_number?: string | null;
  publication_date?: string | null;
  page?: number | null;
}

export interface Conversation {
  id: number;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  conversation_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  model: string | null;
  latency_ms: number | null;
  citations: Citation[];
  created_at: string;
  isStreaming?: boolean;
  error?: string;
}

export interface ChatQueryRequest {
  question: string;
  conversation_id?: number;
  contract_ids?: number[];
  top_k?: number;
  search_mode?: "vector" | "keyword" | "hybrid";
  rerank?: boolean;
}

export interface StreamEvent {
  event: "start" | "token" | "citations" | "guardrails" | "done" | "error";
  data: Record<string, unknown>;
}

export type RiskCategory = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface AnalysisFinding {
  title: string;
  description: string;
  citation: number | null;
}

export interface LegalRisk extends AnalysisFinding {
  severity: RiskCategory;
  reason: string;
}

export interface LegalRecommendation {
  title: string;
  description: string;
  related_risk: string | null;
}

export interface LegalAnalysis {
  analysis_type: "full";
  summary: string;
  risk_score: number;
  risk_category: RiskCategory;
  confidence: number;
  risks: LegalRisk[];
  missing_clauses: AnalysisFinding[];
  ambiguous_clauses: AnalysisFinding[];
  one_sided_clauses: AnalysisFinding[];
  recommendations: LegalRecommendation[];
  citations: Citation[];
}

export type ConfidenceLevel = "VERY_LOW" | "LOW" | "MEDIUM" | "HIGH" | "VERY_HIGH";
export type ClauseType =
  | "CONFIDENTIALITY"
  | "TERMINATION"
  | "PENALTY"
  | "FORCE_MAJEURE"
  | "ARBITRATION"
  | "JURISDICTION"
  | "PAYMENT"
  | "DURATION"
  | "DELIVERY"
  | "KVKK"
  | "NON_COMPETE"
  | "INTELLECTUAL_PROPERTY";
export type RiskTag = "Financial" | "Legal" | "Privacy" | "Commercial" | "Employment";

export interface AttributedSource {
  source_type: "contract" | "law" | "case_law";
  title: string;
  article: string | null;
  page: number | null;
  chunk: number;
  similarity: number;
  rerank_score: number | null;
  text_excerpt: string;
}

export interface ExplainEvidence {
  risk_title: string;
  contract_chunk: AttributedSource | null;
  law_chunk: AttributedSource | null;
  case_law_chunk: AttributedSource | null;
  similarity_score: number;
  rerank_score: number | null;
}

export interface LegalReasoning {
  risk_title: string;
  why_risky: string;
  law_basis: string;
  case_support: string;
  affected_clause: string;
}

export interface RetrievalPathStep {
  stage: string;
  status: string;
  detail: string;
  hit_count: number | null;
}

export interface ExplainableAnalysis {
  analysis: LegalAnalysis;
  confidence_score: number;
  confidence_level: ConfidenceLevel;
  reasoning: LegalReasoning[];
  evidence: ExplainEvidence[];
  retrieval_path: RetrievalPathStep[];
  matched_articles: AttributedSource[];
  matched_cases: AttributedSource[];
  used_contract_chunks: AttributedSource[];
  citations: Citation[];
}

export interface DetectedClause {
  clause_type: ClauseType;
  title: string;
  contract_id: number;
  chunk_id: number;
  chunk_index: number;
  page_number: number | null;
  text: string;
  confidence: number;
  matched_keywords: string[];
  risk_tags: RiskTag[];
}

export interface ClauseListResponse {
  contract_id: number;
  clauses: DetectedClause[];
  detected_types: ClauseType[];
  missing_types: ClauseType[];
}

export type ComplianceStatus = "COMPLIANT" | "PARTIAL" | "NON_COMPLIANT";

export interface ComplianceFinding {
  law: string;
  status: ComplianceStatus;
  required_clauses: ClauseType[];
  detected_clauses: ClauseType[];
  missing_clauses: ClauseType[];
  issues: string[];
  recommendation: string;
}

export interface ComplianceReport {
  contract_id: number;
  compliance_score: number;
  status: ComplianceStatus;
  findings: ComplianceFinding[];
  risk_tags: RiskTag[];
  disclaimer: string;
}

export interface ClauseChange {
  clause_type: ClauseType;
  before: DetectedClause | null;
  after: DetectedClause | null;
  similarity: number;
  summary: string;
}

export interface RiskChange {
  clause_type: ClauseType;
  before_tags: RiskTag[];
  after_tags: RiskTag[];
  direction: string;
}

export interface ContractComparison {
  base_contract_id: number;
  comparison_contract_id: number;
  added_clauses: DetectedClause[];
  removed_clauses: DetectedClause[];
  modified_clauses: ClauseChange[];
  unchanged_clauses: ClauseType[];
  risk_changes: RiskChange[];
  new_obligations: string[];
  new_rights: string[];
  summary: string;
}

export type LegalDocumentType =
  | "LAW"
  | "REGULATION"
  | "COMMUNIQUE"
  | "SUPREME_COURT"
  | "COUNCIL_OF_STATE"
  | "CONSTITUTIONAL_COURT"
  | "OTHER";

export interface LegalDocument {
  id: number;
  title: string;
  document_type: LegalDocumentType;
  source: string;
  official_number: string | null;
  publication_date: string | null;
  language: string;
  status: string;
  original_filename: string;
  file_size: number;
  created_at: string;
  updated_at: string;
}

export interface LegalDocumentListResponse {
  items: LegalDocument[];
  total: number;
}
