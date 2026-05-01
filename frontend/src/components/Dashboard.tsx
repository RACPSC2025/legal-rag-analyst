import React, {
  useState,
  useEffect,
  useRef,
  useMemo,
  useCallback,
} from 'react';
import { Toaster, toast } from 'sonner';
import { pdfjs, Document, Page } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import {
  FileText,
  MessageSquare,
  Database,
  Download,
  Trash2,
  Upload,
  Settings,
  Scale as ScaleIcon,
  BrainCircuit,
  FileCode2,
  ChevronRight,
  Gavel,
  Bold,
  Italic,
  List as ListIcon,
  Loader2,
  Sun,
  Moon,
  Minus,
  Plus,
  Maximize,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  GripVertical,
  Activity,
  Cpu,
  BarChart3,
  Zap,
  BookOpen,
  Hash,
} from 'lucide-react';
import { motion, AnimatePresence, Reorder } from 'motion/react';
import ReactMarkdown from 'react-markdown';

import { useStream } from '../hooks/useStream';
import { uploadDocument, ingestDocument } from '../api/client';
import type {
  Message,
  DocumentInfo,
  CitationOut,
  NumericDiscrepancyOut,
  LegalAnswerResponse,
  StreamPhase,
  VerificationCompleteEvent,
} from '../types';

// ─── Utils ─────────────────────────────────────────────────────────────────

function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

// ─── PDF Worker ────────────────────────────────────────────────────────────

if (typeof window !== 'undefined' && !pdfjs.GlobalWorkerOptions.workerSrc) {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
}

// ─── Sub-components ────────────────────────────────────────────────────────

// ── Confidence badge
function ConfidenceBadge({ score }: { score: number }) {
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
function StreamPhaseIndicator({ phase, phaseMessage, verifyMeta }: { phase: StreamPhase; phaseMessage?: string; verifyMeta: VerificationCompleteEvent | null }) {
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
function CitationCard({ citation, index }: { citation: CitationOut; index: number }) {
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
function DiscrepancyCard({ d }: { d: NumericDiscrepancyOut }) {
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
function VerificationPanel({ answer }: { answer: LegalAnswerResponse }) {
  const [open, setOpen] = useState(false);
  const hasDiscrepancies = answer.numeric_discrepancies.length > 0;
  const allVerified = answer.citations.every((c) => c.is_verified);

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

// ─── Main Dashboard ────────────────────────────────────────────────────────

const Dashboard: React.FC = () => {
  const { phase, phaseMessage, streamingContent, verifyMeta, finalAnswer, error, stream, reset } = useStream();

  const [activeTab, setActiveTab] = useState<'chat' | 'analysis' | 'sources'>('chat');
  const [viewMode, setViewMode] = useState<'pdf' | 'markdown'>('pdf');
  const [zoom, setZoom] = useState(100);
  const [activeDocument, setActiveDocument] = useState<DocumentInfo | null>(null);
  const [documentHistory, setDocumentHistory] = useState<DocumentInfo[]>(() => {
    try {
      const saved = localStorage.getItem('fenix_docs_v2');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      const saved = localStorage.getItem('fenix_chat_v2');
      return saved
        ? JSON.parse(saved)
        : [
            {
              id: '1',
              role: 'assistant',
              content:
                'Bienvenido a **Fénix Legal v2.5**. Soy un analista jurídico con verificación automática de citas. Cada respuesta que genero es auditada contra el corpus documental antes de ser entregada.\n\n¿En qué le puedo asistir?',
              timestamp: new Date().toLocaleTimeString(),
              type: 'markdown',
            },
          ];
    } catch {
      return [];
    }
  });
  const [inputText, setInputText] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [markdownBlocks, setMarkdownBlocks] = useState<{ id: string; content: string }[]>([]);
  const [lastAnswer, setLastAnswer] = useState<LegalAnswerResponse | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingMsgIdRef = useRef<string | null>(null);

  // Persist
  useEffect(() => {
    localStorage.setItem('fenix_docs_v2', JSON.stringify(documentHistory));
  }, [documentHistory]);

  useEffect(() => {
    localStorage.setItem('fenix_chat_v2', JSON.stringify(messages));
  }, [messages]);

  // Dark mode
  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkMode);
  }, [isDarkMode]);

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Sync streaming content → message in progress
  useEffect(() => {
    if (!streamingMsgIdRef.current) return;
    const id = streamingMsgIdRef.current;
    setMessages((prev) =>
      prev.map((m) =>
        m.id === id
          ? { ...m, content: streamingContent, streamPhase: phase, phaseMessage }
          : m
      )
    );
  }, [streamingContent, phase, phaseMessage]);

  // Finalise message when stream completes
  useEffect(() => {
    if (phase === 'complete' && finalAnswer && streamingMsgIdRef.current) {
      const id = streamingMsgIdRef.current;
      setLastAnswer(finalAnswer);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id
            ? {
                ...m,
                content: finalAnswer.answer,
                streamPhase: 'complete',
                legalAnswer: finalAnswer,
                verifyMeta: verifyMeta,
              }
            : m
        )
      );
      streamingMsgIdRef.current = null;
    }
    if (phase === 'error' && error && streamingMsgIdRef.current) {
      const id = streamingMsgIdRef.current;
      setMessages((prev) =>
        prev.map((m) =>
          m.id === id
            ? {
                ...m,
                content: `**Error:** ${error}`,
                streamPhase: 'error',
              }
            : m
        )
      );
      streamingMsgIdRef.current = null;
    }
  }, [phase, finalAnswer, error, verifyMeta]);

  const pdfOptions = useMemo(
    () => ({
      cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
      cMapPacked: true,
      standardFontDataUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`,
    }),
    []
  );

  // Markdown blocks sync
  useEffect(() => {
    if (!activeDocument) { setMarkdownBlocks([]); return; }
    const blocks = (activeDocument as any).markdown
      ?.split(/\n\n+/)
      .filter((b: string) => b.trim())
      .map((b: string, i: number) => ({ id: `${activeDocument.id}-b-${i}`, content: b })) ?? [];
    setMarkdownBlocks((prev) => {
      if (prev.length > 0 && prev[0].id.startsWith(activeDocument.id)) return prev;
      return blocks;
    });
  }, [activeDocument?.id]);

  // ── Format text helpers
  const formatText = (style: 'bold' | 'italic' | 'list') => {
    if (!textareaRef.current) return;
    const { selectionStart: start, selectionEnd: end } = textareaRef.current;
    const selected = inputText.substring(start, end);
    const map = {
      bold: `**${selected}**`,
      italic: `*${selected}*`,
      list: selected.split('\n').map((l) => (l.startsWith('- ') ? l : `- ${l}`)).join('\n'),
    };
    setInputText(inputText.substring(0, start) + map[style] + inputText.substring(end));
  };

  // ── Send message
  const handleSendMessage = useCallback(async () => {
    const query = inputText.trim();
    if (!query || phase === 'generating' || phase === 'verifying') return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString(),
      type: 'text',
    };

    const assistantMsgId = (Date.now() + 1).toString();
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString(),
      type: 'markdown',
      streamPhase: 'generating',
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInputText('');
    streamingMsgIdRef.current = assistantMsgId;

    reset();
    await stream(query);
  }, [inputText, phase, stream, reset]);

  // ── File upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';
    setIsUploading(true);

    const promise = uploadDocument(file);
    toast.promise(promise, {
      loading: 'Subiendo y procesando expediente...',
      success: 'Expediente cargado correctamente',
      error: 'Error al procesar el documento',
    });

    try {
      await promise;
      const newDoc: DocumentInfo = {
        id: Math.random().toString(36).slice(2, 9),
        name: file.name,
        status: 'ready',
        url: URL.createObjectURL(file),
        originalFile: file,
        size: `${(file.size / (1024 * 1024)).toFixed(2)} MB`,
      };
      setActiveDocument(newDoc);
      setDocumentHistory((prev) => [newDoc, ...prev.filter((d) => d.name !== newDoc.name)].slice(0, 10));
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: `Documento **${file.name}** cargado (${newDoc.size}). Ahora puede realizarme consultas sobre su contenido o indexarlo en la base vectorial para búsqueda semántica.`,
          timestamp: new Date().toLocaleTimeString(),
          type: 'markdown',
        },
      ]);
    } catch {
      // handled by toast
    } finally {
      setIsUploading(false);
    }
  };

  // ── Ingest
  const handleIngest = async () => {
    if (!activeDocument) return;
    const promise = ingestDocument();
    toast.promise(promise, {
      loading: 'Indexando en base vectorial...',
      success: (data) => `Indexación completada · ${data.chunks} chunks`,
      error: 'Error en la indexación',
    });
    try {
      await promise;
      setActiveDocument((prev) => prev ? { ...prev, ingested: true } : null);
    } catch { /* handled */ }
  };

  const isStreaming = phase === 'generating' || phase === 'verifying';

  // ─── Render ─────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen bg-surface text-primary font-sans overflow-hidden">
      <Toaster position="top-right" richColors closeButton />

      {/* ── Sidebar ────────────────────────────────────────────────────── */}
      <aside className="w-16 flex flex-col items-center py-8 border-r border-line bg-primary gap-8 shrink-0 shadow-2xl z-20">
        <div className="p-2 bg-accent rounded-xl text-prestige shadow-lg shadow-black/20">
          <ScaleIcon size={24} strokeWidth={2.5} />
        </div>
        <nav className="flex flex-col gap-8">
          <button
            onClick={() => setIsHistoryOpen(!isHistoryOpen)}
            className={cn('p-2 transition-all hover:scale-110 relative', isHistoryOpen ? 'text-accent' : 'text-prestige/40 hover:text-prestige')}
            title="Folios Recientes"
          >
            <Database size={20} />
            {documentHistory.length > 0 && !isHistoryOpen && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-accent rounded-full border border-primary" />
            )}
          </button>
          <button
            onClick={() => setActiveTab('sources')}
            className={cn('p-2 transition-all hover:scale-110', activeTab === 'sources' ? 'text-accent' : 'text-prestige/40 hover:text-prestige')}
            title="Fuentes verificadas"
          >
            <ShieldCheck size={20} />
          </button>
          <button
            onClick={() => setActiveTab('analysis')}
            className={cn('p-2 transition-all hover:scale-110', activeTab === 'analysis' ? 'text-accent' : 'text-prestige/40 hover:text-prestige')}
            title="Dictámenes"
          >
            <Activity size={20} />
          </button>
          <button
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="p-2 text-prestige/40 hover:text-prestige transition-all hover:scale-110"
            title={isDarkMode ? 'Modo Claro' : 'Modo Oscuro'}
          >
            {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </nav>
        <div className="mt-auto mb-4 p-2 text-accent/20">
          <Gavel size={20} />
        </div>
      </aside>

      {/* ── History panel ──────────────────────────────────────────────── */}
      <AnimatePresence>
        {isHistoryOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="h-full bg-prestige/30 border-r border-line flex flex-col shrink-0 overflow-hidden z-10"
          >
            <div className="p-6 border-b border-line flex items-center justify-between">
              <h3 className="text-[11px] font-bold uppercase tracking-[0.3em] text-primary">Folios Recientes</h3>
              <button
                onClick={() => setDocumentHistory([])}
                className="text-[9px] font-bold uppercase tracking-widest text-red-600/40 hover:text-red-600 transition-colors"
              >
                Limpiar
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {documentHistory.length === 0 ? (
                <div className="py-20 text-center px-4">
                  <FileText className="mx-auto text-primary/10 mb-4" size={32} />
                  <p className="text-[10px] text-primary/30 uppercase tracking-widest leading-relaxed">Sin expedientes en el archivo local</p>
                </div>
              ) : (
                documentHistory.map((doc, idx) => (
                  <button
                    key={`${doc.name}-${idx}`}
                    onClick={() => { setActiveDocument(doc); setIsHistoryOpen(false); }}
                    className={cn(
                      'w-full text-left p-4 rounded-xl transition-all border group',
                      activeDocument?.name === doc.name
                        ? 'bg-white border-accent shadow-lg'
                        : 'bg-transparent border-transparent hover:bg-white/50'
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <div className={cn('p-2 rounded-lg', activeDocument?.name === doc.name ? 'bg-accent/10 text-accent' : 'bg-primary/5 text-primary/40')}>
                        <FileText size={16} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-bold truncate mb-1 text-primary/60">{doc.name}</p>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[9px] text-primary/30">{doc.size}</span>
                          {doc.ingested && (
                            <span className="text-[8px] bg-accent/10 text-accent px-1.5 py-0.5 rounded-full font-bold uppercase">Indexado</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Main ───────────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col md:flex-row overflow-hidden relative">

        {/* ── Left: document viewer ─────────────────────────────────── */}
        <section className={cn('flex-1 flex flex-col bg-prestige/50 border-r border-line min-w-0 transition-all duration-500 relative', !activeDocument && 'justify-center items-center')}>
          {activeDocument ? (
            <>
              {/* Toolbar */}
              <div className="flex items-center justify-between p-4 border-b border-line bg-prestige/50">
                <div className="flex items-center gap-3">
                  <div className="p-1.5 bg-primary/5 rounded">
                    <FileText className="text-primary" size={18} />
                  </div>
                  <h2 className="font-serif font-bold text-base text-primary truncate max-w-[200px]">{activeDocument.name}</h2>
                  {activeDocument.ingested && (
                    <span className="text-[9px] font-bold uppercase tracking-widest bg-accent/10 text-accent px-2 py-0.5 rounded-full flex items-center gap-1">
                      <Zap size={8} /> RAG activo
                    </span>
                  )}
                  <div className="flex bg-primary/5 p-1 rounded-full border border-line ml-2 shrink-0">
                    <button onClick={() => setViewMode('pdf')} className={cn('px-3 py-1 text-[10px] uppercase font-bold tracking-widest rounded-full transition-all', viewMode === 'pdf' ? 'bg-primary text-prestige shadow-sm' : 'text-primary/40 hover:text-primary')}>PDF</button>
                    <button onClick={() => setViewMode('markdown')} className={cn('px-3 py-1 text-[10px] uppercase font-bold tracking-widest rounded-full transition-all flex items-center gap-1', viewMode === 'markdown' ? 'bg-primary text-prestige shadow-sm' : 'text-primary/40 hover:text-primary')}>
                      <FileCode2 size={9} /> Estructura
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1 bg-primary/5 p-1 rounded-lg border border-line">
                    <button onClick={() => setZoom((p) => Math.max(50, p - 10))} disabled={zoom <= 50} className="p-1.5 hover:bg-white rounded text-primary/60 hover:text-primary transition-all disabled:opacity-30"><Minus size={14} /></button>
                    <span className="text-[10px] font-bold w-10 text-center text-primary/70">{zoom}%</span>
                    <button onClick={() => setZoom((p) => Math.min(200, p + 10))} disabled={zoom >= 200} className="p-1.5 hover:bg-white rounded text-primary/60 hover:text-primary transition-all disabled:opacity-30"><Plus size={14} /></button>
                    <button onClick={() => setZoom(100)} className="p-1.5 hover:bg-white rounded text-primary/60 hover:text-primary transition-all border-l border-line ml-1"><Maximize size={14} /></button>
                  </div>
                  <button onClick={() => { setActiveDocument(null); setViewMode('pdf'); setZoom(100); }} className="p-2 hover:bg-red-50 text-red-600/60 hover:text-red-600 rounded-lg transition-all">
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>

              {/* Viewer */}
              <div className="flex-1 relative overflow-auto p-8 bg-prestige/30">
                <AnimatePresence mode="wait">
                  {viewMode === 'pdf' ? (
                    <motion.div key="pdf" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="max-w-4xl mx-auto shadow-[0_20px_50px_rgba(0,0,0,0.1)] bg-surface rounded-lg overflow-hidden border border-line">
                      {activeDocument.url ? (
                        <div className="flex flex-col">
                          <div className="sticky top-0 z-20 bg-white/80 backdrop-blur-md border-b border-line px-4 py-2 flex items-center gap-2 shadow-sm">
                            <button onClick={() => setPageNumber((p) => Math.max(p - 1, 1))} disabled={pageNumber <= 1} className="p-1 hover:bg-slate-200 rounded disabled:opacity-30"><ChevronRight className="rotate-180" size={18} /></button>
                            <span className="text-[10px] font-bold uppercase tracking-widest text-primary/60">Pág. {pageNumber} / {numPages ?? '--'}</span>
                            <button onClick={() => setPageNumber((p) => Math.min(p + 1, numPages ?? p))} disabled={pageNumber >= (numPages ?? 1)} className="p-1 hover:bg-slate-200 rounded disabled:opacity-30"><ChevronRight size={18} /></button>
                          </div>
                          <div className="flex justify-center p-4">
                            <Document
                              file={activeDocument.originalFile ?? activeDocument.url}
                              onLoadSuccess={({ numPages: n }) => { setNumPages(n); setPageNumber(1); }}
                              onLoadError={(err) => toast.error(`Error PDF: ${err.message}`)}
                              options={pdfOptions}
                              loading={<div className="flex flex-col items-center p-20 gap-4"><Loader2 className="animate-spin text-accent" size={40} /><p className="text-[10px] font-bold uppercase tracking-widest text-primary/40 animate-pulse">Cargando Folio...</p></div>}
                            >
                              <Page pageNumber={pageNumber} scale={zoom / 100} className="shadow-2xl" loading={null} />
                            </Document>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center justify-center p-20">
                          <p className="text-primary/30 italic font-serif">Vista previa no disponible</p>
                        </div>
                      )}
                    </motion.div>
                  ) : (
                    <motion.div key="markdown" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-4xl mx-auto bg-white border border-line rounded-2xl p-12 shadow-2xl">
                      <div className="relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-8 opacity-[0.03] rotate-12 pointer-events-none"><ScaleIcon size={300} /></div>
                        <p className="text-[10px] font-bold uppercase tracking-[0.4em] text-accent mb-2">Certificación de Estructura Digital</p>
                        <h1 className="text-3xl font-serif font-bold text-primary italic mb-8">{activeDocument.name.replace(/\.[^/.]+$/, '')}</h1>
                        <div className="markdown-body prose prose-slate prose-sm max-w-none">
                          {markdownBlocks.length > 0 ? (
                            <Reorder.Group axis="y" values={markdownBlocks} onReorder={setMarkdownBlocks} className="space-y-4">
                              {markdownBlocks.map((block) => (
                                <Reorder.Item key={block.id} value={block} className="group/item relative bg-surface hover:bg-prestige/30 transition-colors rounded-xl border border-transparent hover:border-line p-2 -m-2">
                                  <div className="absolute -left-6 top-1/2 -translate-y-1/2 opacity-0 group-hover/item:opacity-100 transition-opacity cursor-grab p-1 text-primary/20 hover:text-accent">
                                    <GripVertical size={16} />
                                  </div>
                                  <ReactMarkdown>{block.content}</ReactMarkdown>
                                </Reorder.Item>
                              ))}
                            </Reorder.Group>
                          ) : (
                            <p className="text-primary/30 italic text-center py-12">Sin estructura generada aún.</p>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Actions bar */}
              <div className="px-8 py-6 border-t border-line bg-gradient-to-r from-prestige via-surface to-prestige flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-[10px] font-bold uppercase tracking-[0.3em] text-primary/40 flex items-center gap-2">
                    <div className="w-1 h-3 bg-accent rounded-full" />
                    Inteligencia Jurídica
                  </h4>
                </div>
                <div className="flex gap-3 overflow-x-auto pb-1">
                  <button
                    onClick={handleIngest}
                    disabled={activeDocument.ingested}
                    className="flex items-center gap-3 px-6 py-3 border-2 border-accent/20 bg-accent/5 text-accent text-[11px] font-bold uppercase tracking-widest rounded-xl hover:bg-accent/10 hover:border-accent/40 transition-all shrink-0 group shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <Database size={18} className="group-hover:rotate-12 transition-transform" />
                    {activeDocument.ingested ? 'Indexado ✓' : 'Indexación Vectorial'}
                  </button>
                  <div className="ml-auto flex items-center gap-2 px-4">
                    <span className="text-[9px] font-bold uppercase tracking-tighter text-primary/20">Fénix Legal v2.5</span>
                    <ShieldCheck size={14} className="text-primary/10" />
                  </div>
                </div>
              </div>
            </>
          ) : (
            // Empty state
            <div className="text-center p-12 max-w-lg">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-24 h-24 bg-prestige rounded-full flex items-center justify-center mx-auto mb-8 text-accent shadow-inner border border-line">
                <ScaleIcon size={40} strokeWidth={1.5} />
              </motion.div>
              <h3 className="text-3xl font-serif font-bold text-primary mb-4">Mesa de Análisis Legal</h3>
              <p className="text-primary/60 text-sm mb-10 leading-relaxed font-medium">
                Motor RAG jurídico con verificación automática de citas. Cada respuesta es auditada contra el corpus antes de ser entregada.
              </p>
              <label className={cn('cursor-pointer inline-flex items-center gap-3 px-8 py-4 bg-primary text-prestige text-sm font-bold uppercase tracking-[0.2em] rounded-full hover:bg-primary/95 transition-all active:scale-95 shadow-xl shadow-primary/20 group select-none', isUploading && 'opacity-80 cursor-not-allowed')}>
                {isUploading ? (
                  <><Loader2 size={20} className="animate-spin text-accent" /> Subiendo...</>
                ) : (
                  <><Upload size={20} className="group-hover:-translate-y-1 transition-transform" /> Cargar Expediente</>
                )}
                <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} disabled={isUploading} />
              </label>
            </div>
          )}
        </section>

        {/* ── Right: tabs panel ─────────────────────────────────────── */}
        <section className="w-full md:w-[500px] flex flex-col bg-surface shrink-0 border-l border-line shadow-2xl">
          {/* Tab header */}
          <div className="flex bg-prestige/80 px-4 pt-3 border-b border-line gap-1">
            {(['chat', 'analysis', 'sources'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={cn('px-8 py-4 text-[10px] font-bold uppercase tracking-[0.2em] transition-all relative rounded-t-2xl overflow-hidden group shrink-0', activeTab === tab ? 'text-primary bg-gradient-to-b from-surface to-prestige shadow-[0_-4px_20px_-10px_rgba(0,0,0,0.1)]' : 'text-slate-400 hover:text-primary/60')}
              >
                <span className="relative z-10">
                  {tab === 'chat' && 'Consultoría'}
                  {tab === 'analysis' && 'Dictámenes'}
                  {tab === 'sources' && 'Fuentes'}
                </span>
                {activeTab === tab && (
                  <motion.div layoutId="activeTab" className="absolute bottom-0 left-0 right-0 h-[3px] bg-accent z-20" initial={false} transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }} />
                )}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-hidden relative">
            <AnimatePresence mode="wait">

              {/* ── Tab: Consultoría (chat) ──────────────────────────── */}
              {activeTab === 'chat' && (
                <motion.div key="chat" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="absolute inset-0 flex flex-col p-6">

                  {/* Header */}
                  <div className="flex items-center justify-between mb-4 px-2">
                    <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-primary/40">Historial de Consultas</h4>
                    <button
                      onClick={() => {
                        setMessages([{ id: '1', role: 'assistant', content: 'Historial reiniciado. ¿En qué puedo asistirle?', timestamp: new Date().toLocaleTimeString(), type: 'text' }]);
                        reset();
                        toast.success('Conversación reiniciada');
                      }}
                      className="text-[9px] font-bold uppercase tracking-widest text-red-600/40 hover:text-red-600 transition-colors flex items-center gap-1.5"
                    >
                      <Trash2 size={10} /> Limpiar
                    </button>
                  </div>

                  {/* Messages */}
                  <div className="flex-1 overflow-y-auto space-y-6 pr-2 mb-4 scroll-smooth">
                    {messages.map((msg) => (
                      <div key={msg.id} className={cn('flex flex-col gap-2 max-w-[92%]', msg.role === 'user' ? 'ml-auto items-end' : 'mr-auto items-start')}>
                        <div className={cn('px-5 py-4 rounded-3xl text-[13px] leading-relaxed shadow-sm', msg.role === 'user' ? 'bg-primary text-prestige rounded-tr-none' : 'bg-surface text-primary border border-line rounded-tl-none')}>
                          {msg.role === 'assistant' && msg.streamPhase === 'generating' && !msg.content && (
                            <div className="flex gap-1.5 items-center h-5">
                              <motion.span animate={{ scale: [1, 1.4, 1] }} transition={{ repeat: Infinity, duration: 0.8, delay: 0 }} className="w-1.5 h-1.5 rounded-full bg-accent/60" />
                              <motion.span animate={{ scale: [1, 1.4, 1] }} transition={{ repeat: Infinity, duration: 0.8, delay: 0.15 }} className="w-1.5 h-1.5 rounded-full bg-accent/60" />
                              <motion.span animate={{ scale: [1, 1.4, 1] }} transition={{ repeat: Infinity, duration: 0.8, delay: 0.3 }} className="w-1.5 h-1.5 rounded-full bg-accent/60" />
                            </div>
                          )}
                          {msg.content && (
                            <div className="markdown-body prose prose-slate prose-sm max-w-none dark:prose-invert">
                              <ReactMarkdown>{msg.content}</ReactMarkdown>
                            </div>
                          )}
                          {msg.legalAnswer && <VerificationPanel answer={msg.legalAnswer} />}
                        </div>

                        {/* Stream phase pill — only on current streaming message */}
                        {msg.streamPhase && msg.streamPhase !== 'complete' && msg.streamPhase !== 'idle' && (
                          <AnimatePresence>
                            <StreamPhaseIndicator phase={msg.streamPhase} phaseMessage={msg.phaseMessage as string} verifyMeta={verifyMeta} />
                          </AnimatePresence>
                        )}

                        <span className="text-[9px] uppercase tracking-widest text-primary/40 font-bold px-2">{msg.timestamp}</span>
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>

                  {/* Input */}
                  <div className="mt-auto bg-prestige/50 border border-line p-1.5 rounded-[2rem] shadow-lg shadow-black/5 focus-within:ring-2 focus-within:ring-primary/5 transition-all">
                    <div className="flex px-4 py-2 border-b border-line/50 mb-1 gap-1">
                      <button onClick={() => formatText('bold')} className="p-1.5 text-slate-400 hover:text-primary hover:bg-prestige rounded-full transition-colors" title="Negrita"><Bold size={14} /></button>
                      <button onClick={() => formatText('italic')} className="p-1.5 text-slate-400 hover:text-primary hover:bg-prestige rounded-full transition-colors" title="Cursiva"><Italic size={14} /></button>
                      <button onClick={() => formatText('list')} className="p-1.5 text-slate-400 hover:text-primary hover:bg-prestige rounded-full transition-colors" title="Lista"><ListIcon size={14} /></button>
                    </div>
                    <div className="relative flex items-end">
                      <textarea
                        ref={textareaRef}
                        value={inputText}
                        onChange={(e) => setInputText(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); } }}
                        placeholder="Consulte su criterio jurídico..."
                        className="flex-1 bg-transparent px-5 py-3 text-sm text-primary focus:outline-none resize-none h-20 min-h-[80px] placeholder:text-primary/30"
                        disabled={isStreaming}
                      />
                      <button
                        onClick={handleSendMessage}
                        disabled={!inputText.trim() || isStreaming}
                        className="m-2 p-3 bg-primary text-prestige rounded-full hover:bg-primary/95 disabled:opacity-50 transition-all active:scale-90 shadow-lg shadow-primary/20"
                      >
                        {isStreaming ? <Loader2 size={20} className="animate-spin" /> : <ChevronRight size={20} />}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 justify-center mt-4">
                    <label className="cursor-pointer group flex items-center gap-1.5 text-[9px] uppercase font-bold tracking-[0.2em] text-primary/40 hover:text-accent transition-colors">
                      <Upload size={12} className="group-hover:-translate-y-0.5 transition-transform" /> Anexo
                      <input type="file" className="hidden" onChange={handleFileUpload} />
                    </label>
                    <div className="h-1 w-1 bg-accent/20 rounded-full" />
                    <span className="text-[9px] uppercase font-bold tracking-[0.2em] text-primary/40">Verificación Automática · Fénix Legal v2.5</span>
                  </div>
                </motion.div>
              )}

              {/* ── Tab: Dictámenes (last answer full view) ───────────── */}
              {activeTab === 'analysis' && (
                <motion.div key="analysis" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 p-8 overflow-y-auto">
                  <div className="bg-prestige border border-line rounded-2xl p-8 shadow-sm relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-1.5 h-full bg-accent" />
                    <h3 className="font-serif font-bold text-2xl text-primary mb-2 flex items-center justify-between">
                      Último Dictamen
                      <FileText size={20} className="text-accent/30" />
                    </h3>
                    {lastAnswer && (
                      <div className="flex items-center gap-2 mb-6">
                        <ConfidenceBadge score={lastAnswer.confidence_score} />
                        {lastAnswer.requires_human_review && (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest border border-amber-200 text-amber-700 bg-amber-50">
                            <AlertTriangle size={10} /> Revisión requerida
                          </span>
                        )}
                        {lastAnswer.verification_meta && (
                          <span className="text-[9px] text-primary/30 font-mono ml-auto">
                            {lastAnswer.verification_meta.duration_ms.toFixed(0)}ms · intento {lastAnswer.verification_meta.attempt}
                          </span>
                        )}
                      </div>
                    )}
                    <div className="markdown-body prose prose-slate prose-sm dark:prose-invert max-w-none">
                      {lastAnswer ? (
                        <ReactMarkdown>{lastAnswer.answer}</ReactMarkdown>
                      ) : (
                        <div className="py-12 text-center">
                          <BrainCircuit size={48} className="mx-auto text-primary/10 mb-4" />
                          <p className="text-primary/40 italic font-serif">Sin dictamen generado. Realice una consulta en la pestaña Consultoría.</p>
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              )}

              {/* ── Tab: Fuentes verificadas ───────────────────────────── */}
              {activeTab === 'sources' && (
                <motion.div key="sources" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="absolute inset-0 p-6 overflow-y-auto">
                  <div className="mb-4 px-2">
                    <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-primary/40 mb-1">Fuentes Verificadas</h4>
                    <p className="text-[11px] text-primary/30">Citas del último dictamen auditadas por el Citation Verifier.</p>
                  </div>

                  {lastAnswer ? (
                    <div className="space-y-4">
                      {/* Metrics */}
                      {lastAnswer.verification_meta && (
                        <div className="grid grid-cols-3 gap-2">
                          {[
                            { label: 'Verificadas', value: lastAnswer.verification_meta.verified_count, color: 'text-emerald-600' },
                            { label: 'Fallidas', value: lastAnswer.verification_meta.failed_count, color: 'text-red-500' },
                            { label: 'Tiempo', value: `${lastAnswer.verification_meta.duration_ms.toFixed(0)}ms`, color: 'text-primary/60' },
                          ].map((m) => (
                            <div key={m.label} className="bg-prestige border border-line rounded-xl p-3 text-center">
                              <p className={cn('text-xl font-bold font-mono', m.color)}>{m.value}</p>
                              <p className="text-[9px] uppercase tracking-widest text-primary/30 font-bold">{m.label}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Citations */}
                      {lastAnswer.citations.length > 0 && (
                        <div className="space-y-2">
                          {lastAnswer.citations.map((c, i) => (
                            <CitationCard key={c.article_id + i} citation={c} index={i} />
                          ))}
                        </div>
                      )}

                      {/* Discrepancies */}
                      {lastAnswer.numeric_discrepancies.length > 0 && (
                        <div>
                          <p className="text-[9px] font-bold uppercase tracking-[0.2em] text-primary/30 mb-2 flex items-center gap-1.5 px-1">
                            <AlertTriangle size={9} /> Discrepancias numéricas
                          </p>
                          <div className="space-y-2">
                            {lastAnswer.numeric_discrepancies.map((d, i) => (
                              <DiscrepancyCard key={i} d={d} />
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="py-20 text-center">
                      <ShieldCheck size={48} className="mx-auto text-primary/10 mb-4" />
                      <p className="text-primary/40 italic font-serif text-sm">Sin consultas verificadas aún.</p>
                    </div>
                  )}
                </motion.div>
              )}

            </AnimatePresence>
          </div>
        </section>
      </main>

      {/* ── Upload overlay ─────────────────────────────────────────────── */}
      <AnimatePresence>
        {isUploading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-primary/20 backdrop-blur-md z-50 flex flex-col items-center justify-center">
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: 'linear' }} className="w-16 h-16 border-4 border-prestige/20 border-t-accent rounded-full mb-6 shadow-xl" />
            <p className="text-sm font-bold uppercase tracking-[0.4em] text-white drop-shadow-lg">Ingestando Expediente</p>
            <p className="text-[10px] text-prestige/60 mt-2 uppercase tracking-widest">Protocolo de seguridad activo</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Dashboard;
