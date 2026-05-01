import React from 'react';
import {
  Database,
  ShieldCheck,
  Activity,
  Sun,
  Moon,
  Scale as ScaleIcon,
  Gavel
} from 'lucide-react';
import type { DocumentInfo } from '../../../types';

interface SidebarProps {
  isHistoryOpen: boolean;
  setIsHistoryOpen: (open: boolean) => void;
  activeTab: string;
  setActiveTab: (tab: 'chat' | 'analysis' | 'sources') => void;
  isDarkMode: boolean;
  setIsDarkMode: (dark: boolean) => void;
  documentHistory: DocumentInfo[];
}

function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function Sidebar({
  isHistoryOpen,
  setIsHistoryOpen,
  activeTab,
  setActiveTab,
  isDarkMode,
  setIsDarkMode,
  documentHistory,
}: SidebarProps) {
  return (
    <aside className="w-16 flex flex-col items-center py-8 border-r border-line bg-primary gap-8 shrink-0 shadow-2xl z-20">
      <div className="p-2 bg-accent rounded-xl text-prestige shadow-lg shadow-black/20">
        <ScaleIcon size={24} strokeWidth={2.5} />
      </div>
      <nav className="flex flex-col gap-8">
        <button
          onClick={() => setIsHistoryOpen(!isHistoryOpen)}
          className={cn(
            'p-2 transition-all hover:scale-110 relative',
            isHistoryOpen ? 'text-accent' : 'text-prestige/40 hover:text-prestige'
          )}
          title="Folios Recientes"
        >
          <Database size={20} />
          {documentHistory.length > 0 && !isHistoryOpen && (
            <span className="absolute top-1 right-1 w-2 h-2 bg-accent rounded-full border border-primary" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('sources')}
          className={cn(
            'p-2 transition-all hover:scale-110',
            activeTab === 'sources' ? 'text-accent' : 'text-prestige/40 hover:text-prestige'
          )}
          title="Fuentes verificadas"
        >
          <ShieldCheck size={20} />
        </button>
        <button
          onClick={() => setActiveTab('analysis')}
          className={cn(
            'p-2 transition-all hover:scale-110',
            activeTab === 'analysis' ? 'text-accent' : 'text-prestige/40 hover:text-prestige'
          )}
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
  );
}
