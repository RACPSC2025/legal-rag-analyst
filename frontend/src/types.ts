export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  type?: 'text' | 'markdown' | 'analysis';
  streamPhase?: StreamPhase;
  phaseMessage?: string;
  legalAnswer?: any;
  verifyMeta?: any;
}

export interface DocumentInfo {
  id: string;
  name: string;
  status: 'idle' | 'processing' | 'ready';
  url?: string;
  originalFile?: File;
  analysis?: string;
  markdown?: string;
  size?: string;
}

// ─── LegalAnswerResponse (Fase 3: Generación Verificable) ───

export interface CitationOut {
  article_id: string;
  source_doc: string;
  quote: string;
  relevance_score: number;
  is_verified: boolean;
  verification_note: string;
}

export interface NumericDiscrepancyOut {
  field_name: string;
  expected_value: string;
  found_value: string;
  source_table: string;
  data_type: string;
}

export interface VerificationMetaOut {
  verified_count: number;
  failed_count: number;
  duration_ms: number;
  attempt: number;
}

export interface LegalAnswerResponse {
  request_id: string;
  answer: string;
  citations: CitationOut[];
  confidence_score: number;
  requires_human_review: boolean;
  numeric_discrepancies: NumericDiscrepancyOut[];
  verification_meta?: VerificationMetaOut;
}

// ─── Eventos de Streaming (astream_events v2) ───

export type StreamPhase = 'idle' | 'generating' | 'verifying' | 'delivery' | 'complete' | 'error';

export interface TokenEvent {
  content: string;
}

export interface VerificationStartEvent {
  message: string;
}

export interface VerificationCompleteEvent {
  verified: number;
  failed: number;
  verification_passed: boolean;
}

export interface IngestionResponse {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  processed_files: string[];
  failed_files: string[];
  total_chunks: number;
  indexed_chunks: number;
  errors: string[];
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
}
