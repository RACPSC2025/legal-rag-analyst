import type { LegalAnswerResponse, IngestionResponse } from '../types';

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

// ─── Document upload & Ingestion ───────────────────────────────────────────

export interface ProcessedDoc {
  filename: string;
  file_paths: string[];
}

export async function uploadDocument(file: File): Promise<ProcessedDoc> {
  const formData = new FormData();
  formData.append('files', file); // API expects 'files' list
  const res = await fetch(`${BASE}/ingestion/upload`, { method: 'POST', body: formData });
  if (!res.ok) throw new Error('Error al subir el documento');
  return res.json();
}

export async function startIngestion(filePaths: string[]): Promise<IngestionResponse> {
  const res = await fetch(`${BASE}/ingestion`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_paths: filePaths }),
  });
  if (!res.ok) throw new Error('Error iniciando la ingesta');
  return res.json();
}

export async function getIngestionStatus(jobId: string): Promise<IngestionResponse> {
  const res = await fetch(`${BASE}/ingestion/status/${jobId}`);
  if (!res.ok) throw new Error('Error consultando el estado de ingesta');
  return res.json();
}

/**
 * Realiza el flujo completo de ingesta con polling
 */
export async function processIngestion(filePaths: string[], onProgress?: (status: string) => void): Promise<IngestionResponse> {
  let job = await startIngestion(filePaths);
  
  while (job.status === 'queued' || job.status === 'processing') {
    if (onProgress) onProgress(job.status);
    await new Promise(r => setTimeout(r, 2000));
    job = await getIngestionStatus(job.job_id);
  }
  
  return job;
}
