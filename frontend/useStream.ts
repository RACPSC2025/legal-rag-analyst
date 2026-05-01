import { useCallback, useRef, useState } from 'react';
import type {
  LegalAnswerResponse,
  StreamPhase,
  TokenEvent,
  VerificationCompleteEvent,
} from './src/types';

interface PhaseChangeEvent {
  phase: StreamPhase;
  message: string;
}

interface UseStreamReturn {
  phase: StreamPhase;
  phaseMessage: string;
  streamingContent: string;
  verifyMeta: VerificationCompleteEvent | null;
  finalAnswer: LegalAnswerResponse | null;
  error: string | null;
  stream: (query: string, topK?: number) => Promise<LegalAnswerResponse | null>;
  reset: () => void;
}

export function useStream(): UseStreamReturn {
  const [phase, setPhase] = useState<StreamPhase>('idle');
  const [phaseMessage, setPhaseMessage] = useState('');
  const [streamingContent, setStreamingContent] = useState('');
  const [verifyMeta, setVerifyMeta] = useState<VerificationCompleteEvent | null>(null);
  const [finalAnswer, setFinalAnswer] = useState<LegalAnswerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setPhase('idle');
    setPhaseMessage('');
    setStreamingContent('');
    setVerifyMeta(null);
    setFinalAnswer(null);
    setError(null);
  }, []);

  const stream = useCallback(
    async (query: string, topK = 5): Promise<LegalAnswerResponse | null> => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      reset();
      setPhase('generating');

      try {
        const response = await fetch('/api/v1/query/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: query, top_k: topK, include_tables: true, use_cache: true }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let resolved: LegalAnswerResponse | null = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split('\n\n');
          buffer = frames.pop() ?? '';

          for (const frame of frames) {
            const lines = frame.split('\n');
            const eventLine = lines.find((l) => l.startsWith('event:'));
            const dataLine = lines.find((l) => l.startsWith('data:'));
            if (!eventLine || !dataLine) continue;

            const eventName = eventLine.replace('event:', '').trim();
            let payload: unknown;
            try {
              payload = JSON.parse(dataLine.replace('data:', '').trim());
            } catch {
              continue;
            }

            switch (eventName) {
              case 'token': {
                const ev = payload as TokenEvent;
                setStreamingContent((prev) => prev + ev.content);
                break;
              }
              case 'phase_change': {
                const ev = payload as PhaseChangeEvent;
                setPhase(ev.phase);
                setPhaseMessage(ev.message);
                console.debug('[stream] phase_change', ev);
                break;
              }
              case 'verification_complete': {
                const ev = payload as VerificationCompleteEvent;
                setVerifyMeta(ev);
                break;
              }
              case 'final_response': {
                const ev = payload as LegalAnswerResponse;
                setFinalAnswer(ev);
                setPhase('complete');
                resolved = ev;
                break;
              }
              case 'error': {
                const ev = payload as { message: string, details?: string };
                setError(ev.message);
                setPhase('error');
                break;
              }
              case 'start':
              case 'end':
                break;
            }
          }

          if (phase === 'complete' || phase === 'error') break;
        }

        return resolved;
      } catch (err: unknown) {
        if ((err as Error).name === 'AbortError') return null;
        const msg = err instanceof Error ? err.message : 'Error desconocido';
        setError(msg);
        setPhase('error');
        return null;
      }
    },
    [reset, phase]
  );

  return { phase, phaseMessage, streamingContent, verifyMeta, finalAnswer, error, stream, reset };
}

