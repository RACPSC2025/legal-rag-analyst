import React, { useMemo } from 'react';
import { pdfjs, Document, Page } from 'react-pdf';
import { motion, AnimatePresence } from 'motion/react';
import { Loader2, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';

// ─── PDF Worker ────────────────────────────────────────────────────────────
if (typeof window !== 'undefined' && !pdfjs.GlobalWorkerOptions.workerSrc) {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
}

interface PdfViewerProps {
  file: File | string;
  pageNumber: number;
  setPageNumber: (p: (prev: number) => number) => void;
  numPages: number | null;
  setNumPages: (n: number) => void;
  zoom: number;
}

export function PdfViewer({
  file,
  pageNumber,
  setPageNumber,
  numPages,
  setNumPages,
  zoom,
}: PdfViewerProps) {
  const pdfOptions = useMemo(
    () => ({
      cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
      cMapPacked: true,
      standardFontDataUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`,
    }),
    []
  );

  return (
    <motion.div
      key="pdf"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="max-w-4xl mx-auto shadow-[0_20px_50px_rgba(0,0,0,0.1)] bg-surface rounded-lg overflow-hidden border border-line"
    >
      <div className="flex flex-col">
        <div className="sticky top-0 z-20 bg-white/80 backdrop-blur-md border-b border-line px-4 py-2 flex items-center gap-2 shadow-sm">
          <button
            onClick={() => setPageNumber((p) => Math.max(p - 1, 1))}
            disabled={pageNumber <= 1}
            className="p-1 hover:bg-slate-200 rounded disabled:opacity-30"
          >
            <ChevronRight className="rotate-180" size={18} />
          </button>
          <span className="text-[10px] font-bold uppercase tracking-widest text-primary/60">
            Pág. {pageNumber} / {numPages ?? '--'}
          </span>
          <button
            onClick={() => setPageNumber((p) => Math.min(p + 1, numPages ?? p))}
            disabled={pageNumber >= (numPages ?? 1)}
            className="p-1 hover:bg-slate-200 rounded disabled:opacity-30"
          >
            <ChevronRight size={18} />
          </button>
        </div>
        <div className="flex justify-center p-4">
          <Document
            file={file}
            onLoadSuccess={({ numPages: n }) => {
              setNumPages(n);
              setPageNumber(() => 1);
            }}
            onLoadError={(err) => toast.error(`Error PDF: ${err.message}`)}
            options={pdfOptions}
            loading={
              <div className="flex flex-col items-center p-20 gap-4">
                <Loader2 className="animate-spin text-accent" size={40} />
                <p className="text-[10px] font-bold uppercase tracking-widest text-primary/40 animate-pulse">
                  Cargando Folio...
                </p>
              </div>
            }
          >
            <Page pageNumber={pageNumber} scale={zoom / 100} className="shadow-2xl" loading={null} />
          </Document>
        </div>
      </div>
    </motion.div>
  );
}
