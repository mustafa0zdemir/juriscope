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
  event: "start" | "token" | "citations" | "done" | "error";
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
