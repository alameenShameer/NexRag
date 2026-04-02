import { Brain, Settings, Moon, Sun, Database } from 'lucide-react';

export function Navbar({ 
  onEditKG, 
  isDark, 
  onToggleTheme 
}: { 
  onEditKG?: () => void;
  isDark?: boolean;
  onToggleTheme?: () => void;
}) {
  return (
    <div className="h-16 border-b border-border bg-card px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
          <Brain className="w-6 h-6 text-primary-foreground" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-foreground">NexRAG AI</h1>
          <p className="text-xs text-muted-foreground">Hybrid Intelligence for Academic Queries</p>
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted/50 border border-border">
          <div className="w-2 h-2 rounded-full bg-foreground animate-pulse"></div>
          <span className="text-xs text-muted-foreground">Mistral (Local)</span>
        </div>
        
        <button 
          onClick={onToggleTheme}
          className="w-9 h-9 rounded-lg hover:bg-muted/50 flex items-center justify-center transition-colors"
          title="Toggle Theme"
        >
          {isDark ? (
            <Sun className="w-4 h-4 text-muted-foreground" />
          ) : (
            <Moon className="w-4 h-4 text-muted-foreground" />
          )}
        </button>
        
        <button 
          onClick={onEditKG}
          title="Manage Knowledge Base"
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
        >
          <Database className="w-4 h-4" />
          <span className="text-xs font-medium">Knowledge Base</span>
        </button>
      </div>
    </div>
  );
}