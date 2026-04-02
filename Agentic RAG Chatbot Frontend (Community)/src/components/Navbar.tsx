import { Brain, Settings, Moon } from 'lucide-react';

export function Navbar() {
  return (
    <div className="h-16 border-b border-border bg-card px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center">
          <Brain className="w-6 h-6 text-black" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-foreground">NexRAG AI</h1>
          <p className="text-xs text-muted-foreground">Hybrid Intelligence for Academic Queries</p>
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-muted/50 border border-border">
          <div className="w-2 h-2 rounded-full bg-white animate-pulse"></div>
          <span className="text-xs text-muted-foreground">Mistral (Local)</span>
        </div>
        
        <button className="w-9 h-9 rounded-lg hover:bg-muted/50 flex items-center justify-center transition-colors">
          <Moon className="w-4 h-4 text-muted-foreground" />
        </button>
        
        <button className="w-9 h-9 rounded-lg hover:bg-muted/50 flex items-center justify-center transition-colors">
          <Settings className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>
    </div>
  );
}