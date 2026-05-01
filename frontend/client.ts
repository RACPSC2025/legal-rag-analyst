import type { LegalAnswerResponse } from './src/types';

const BASE = '/api/v1';

// ─── Health check ──────────────────────────────────────────────────────────

export async function healthCheck(): Promise<{ status: string; phase: string }> {
  const res = await fetch(`/health`);
  if (!res.ok) throw new Error('Backend no disponible');
  return res.json();
}

// ─── Query síncrona (fallback sin streaming) ───────────────────────────────

export async function querySync(
  query: string,
  topK = 5
): Promise<LegalAnswerResponse> {
  const res = await fetch(`${BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: query, top_k: topK, include_tables: true }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail?.error ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// ─── Document upload ───────────────────────────────────────────────────────

export interface ProcessedDoc {
  filename: string;
  size: number;
  status: string;
  tokensEstimated: number;
}

export async function uploadDocument(file: File): Promise<ProcessedDoc> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch('/api/process-pdf', { method: 'POST', body: formData });
  if (!res.ok) throw new Error('Error procesando el documento');
  return res.json();
}

// ─── Vectorize ─────────────────────────────────────────────────────────────

export interface IngestResult {
  message: string;
  chunks: number;
  indexId: string;
}

export async function ingestDocument(): Promise<IngestResult> {
  const res = await fetch('/api/vectorize', { method: 'POST' });
  if (!res.ok) throw new Error('Error en la indexación vectorial');
  return res.json();
}
