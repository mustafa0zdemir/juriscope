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
}

export interface UploadResponse {
  filename: string;
  size: number;
  content_type: string;
  message: string;
}

export interface Citation {
  contract_id: number;
  chunk_id: number;
  chunk_index: number;
  page_number: number | null;
  score: number;
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
