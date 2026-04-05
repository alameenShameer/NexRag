import { Database, Moon, Sun } from 'lucide-react';
import { BrandMark } from './BrandMark';

interface SystemStatus {
  state?: 'loading' | 'ready' | 'error';
  message?: string;
  pdfs: number;
  official_documents?: number;
  chunks: number;
  vector_ready: boolean;
  kg_ready: boolean;
  llm_provider: string;
  llm_model: string;
  index_version?: string;
}

export function Navbar({
  onEditKG,
  isDark,
  onToggleTheme,
  status,
}: {
  onEditKG?: () => void;
  isDark?: boolean;
  onToggleTheme?: () => void;
  status?: SystemStatus | null;
}) {
  const backendReady = Boolean(status?.vector_ready || status?.kg_ready);
  const readinessState = status?.state || (backendReady ? 'ready' : 'loading');

  return (
    <div className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
      <div className="flex items-center gap-3">
        <BrandMark size={40} theme={isDark ? 'dark' : 'light'} />
        <div>
          <h1 className="text-lg font-semibold text-foreground">NexRag</h1>
          <p className="text-xs text-muted-foreground">Hybrid Intelligence for Academic Queries</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-3 py-1.5">
          <div
            className={`h-2 w-2 rounded-full ${
              readinessState === 'ready'
                ? 'bg-emerald-400 animate-pulse'
                : readinessState === 'error'
                  ? 'bg-rose-400'
                  : 'bg-amber-400 animate-pulse'
            }`}
          />
          <span className="text-xs text-muted-foreground">
            {status ? `${status.message || 'Backend ready'} | ${status.llm_model} (${status.llm_provider})` : 'Backend status unavailable'}
          </span>
        </div>

        <button
          onClick={onToggleTheme}
          className="flex h-9 w-9 items-center justify-center rounded-lg transition-colors hover:bg-muted/50"
          title="Toggle Theme"
        >
          {isDark ? (
            <Sun className="h-4 w-4 text-muted-foreground" />
          ) : (
            <Moon className="h-4 w-4 text-muted-foreground" />
          )}
        </button>

        <button
          onClick={onEditKG}
          title="Manage Knowledge Base"
          className="flex items-center gap-2 rounded-lg bg-primary/10 px-3 py-1.5 text-primary transition-colors hover:bg-primary/20"
        >
          <Database className="h-4 w-4" />
          <span className="text-xs font-medium">Knowledge Base</span>
        </button>
      </div>
    </div>
  );
}
