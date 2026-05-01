import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  BarChart3,
  BookOpen,
  Hash,
  ChevronRight,
  Cpu
} from 'lucide-react';
import type {
  CitationOut,
  NumericDiscrepancyOut,
  LegalAnswerResponse,
  StreamPhase,
  VerificationCompleteEvent
} from '../../../types';

function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

// ── Confidence badge
export function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 85
      ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
      : pct >= 60
      ? 'text-amber-700 bg-amber-50 border-amber-200'
      : 'text-red-700 bg-red-50 border-red-200';
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest border',
        color
      )}
    >
      <BarChart3 size={10} />
      {pct}% confianza
    </span>
  );
}

// ── Stream phase indicator
export function StreamPhaseIndicator({ phase, phaseMessage, verifyMeta }: { phase: StreamPhase; phaseMessage?: string; verifyMeta: VerificationCompleteEvent | null }) {
  if (phase === 'idle' || phase === 'complete' || phase === 'error') return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      className="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-primary/5 border border-line text-[10px] font-bold uppercase tracking-widest text-primary/60"
    >
      {phase === 'generating' && (
        <>
          <Cpu size={12} className="text-accent animate-pulse" />
          <span>{phaseMessage || 'Generando respuesta...'}</span>
        </>
      )}
      {phase === 'verifying' && (
        <>
          <ShieldCheck size={12} className="text-accent animate-pulse" />
          <span>
            {phaseMessage || 'Verificando citas'}
            {verifyMeta !== null
              ? ` · ${verifyMeta.verified_count} ok / ${verifyMeta.failed_count} fallidos`
              : '...'}
          </span>
        </>
      )}
      {phase === 'delivery' && (
        <>
          <CheckCircle2 size={12} className="text-emerald-500 animate-pulse" />
          <span>{phaseMessage || 'Entregando...'}</span>
        </>
      )}
    </motion.div>
  );
}

// ── Citation card
export function CitationCard({ citation, index }: { citation: CitationOut; index: number }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className={cn(
        'rounded-xl border p-3 text-[11px] transition-all cursor-pointer',
        citation.is_verified
          ? 'border-emerald-200 bg-emerald-50/50 hover:bg-emerald-50'
          : 'border-red-200 bg-red-50/50 hover:bg-red-50'
      )}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start gap-2">
        {citation.is_verified ? (
          <CheckCircle2 size={14} className="text-emerald-600 shrink-0 mt-0.5" />
        ) : (
          <XCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="font-bold text-primary font-mono">{citation.article_id}</span>
            <span className="text-primary/40">·</span>
            <span className="text-primary/60 truncate">{citation.source_doc}</span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full',
                citation.is_verified
                  ? 'text-emerald-700 bg-emerald-100'
                  : 'text-red-700 bg-red-100'
              )}
            >
              {citation.is_verified ? 'Verificada' : 'No verificada'}
            </span>
            <span className="text-[9px] text-primary/40">
              relevancia {Math.round(citation.relevance_score * 100)}%
            </span>
          </div>
        </div>
      </div>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-2.5 pt-2.5 border-t border-current/10 space-y-1.5">
              <p className="text-primary/70 italic leading-relaxed">&ldquo;{citation.quote}&rdquo;</p>
              {citation.verification_note && (
                <p className="text-[10px] text-primary/40">{citation.verification_note}</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Numeric discrepancy card
export function DiscrepancyCard({ d }: { d: NumericDiscrepancyOut }) {
  const typeLabel: Record<string, string> = {
    currency: 'Monetario',
    days: 'Plazo (días)',
    months: 'Plazo (meses)',
    years: 'Plazo (años)',
    percentages: 'Porcentaje',
    smmlv: 'SMMLV',
  };
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-3 text-[11px]">
      <div className="flex items-center gap-2 mb-1.5">
        <AlertTriangle size={12} className="text-amber-600" />
        <span className="font-bold text-primary">{d.field_name}</span>
        <span className="text-[9px] uppercase tracking-wider text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded-full font-bold">
          {typeLabel[d.data_type] ?? d.data_type}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-[9px] text-primary/40 uppercase tracking-wider mb-0.5">Esperado</p>
          <p className="font-bold text-emerald-700 font-mono">{d.expected_value}</p>
        </div>
        <div>
          <p className="text-[9px] text-primary/40 uppercase tracking-wider mb-0.5">Encontrado</p>
          <p className="font-bold text-red-600 font-mono">{d.found_value}</p>
        </div>
      </div>
      <p className="text-[9px] text-primary/40 mt-1.5 truncate">Fuente: {d.source_table}</p>
    </div>
  );
}

// ── Verification panel (shown in message)
export function VerificationPanel({ answer }: { answer: LegalAnswerResponse }) {
  const [open, setOpen] = useState(false);
  const hasDiscrepancies = answer.numeric_discrepancies.length > 0;

  return (
    <div className="mt-3 border-t border-line/50 pt-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full text-left"
      >
        <div className="flex items-center gap-2 flex-1">
          {answer.requires_human_review ? (
            <AlertTriangle size={12} className="text-amber-500" />
          ) : (
            <ShieldCheck size={12} className="text-emerald-500" />
          )}
          <span className="text-[10px] font-bold uppercase tracking-widest text-primary/50">
            {answer.requires_human_review ? 'Revisión humana requerida' : 'Verificado automáticamente'}
          </span>
          <ConfidenceBadge score={answer.confidence_score} />
          {answer.verification_meta && (
            <span className="text-[9px] text-primary/30 font-mono ml-auto">
              {answer.verification_meta.duration_ms.toFixed(0)}ms · intento {answer.verification_meta.attempt}
            </span>
          )}
        </div>
        <ChevronRight
          size={12}
          className={cn('text-primary/30 transition-transform', open && 'rotate-90')}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-2">
              {answer.requires_human_review && (
                <div className="flex items-start gap-2 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-[11px] text-amber-800">
                  <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                  <span>
                    Esta respuesta no superó la verificación automática completa.
                    Consulte el documento original antes de usar esta información.
                  </span>
                </div>
              )}

              {answer.citations.length > 0 && (
                <div>
                  <p className="text-[9px] font-bold uppercase tracking-[0.2em] text-primary/30 mb-1.5 flex items-center gap-1.5">
                    <BookOpen size={9} /> Citas ({answer.citations.length})
                  </p>
                  <div className="space-y-1.5">
                    {answer.citations.map((c, i) => (
                      <CitationCard key={c.article_id + i} citation={c} index={i} />
                    ))}
                  </div>
                </div>
              )}

              {hasDiscrepancies && (
                <div>
                  <p className="text-[9px] font-bold uppercase tracking-[0.2em] text-primary/30 mb-1.5 flex items-center gap-1.5">
                    <Hash size={9} /> Discrepancias numéricas ({answer.numeric_discrepancies.length})
                  </p>
                  <div className="space-y-1.5">
                    {answer.numeric_discrepancies.map((d, i) => (
                      <DiscrepancyCard key={i} d={d} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
