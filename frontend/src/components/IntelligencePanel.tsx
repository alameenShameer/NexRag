import { FileText, Network, Activity, CheckCircle2 } from 'lucide-react';
import { useState, useEffect } from 'react';

type TabType = 'sources' | 'knowledge-graph' | 'system-status';

interface SourceChunk {
  id: string;
  fileName: string;
  page: number;
  content: string;
  relevance: number;
}

export function IntelligencePanel({ snippets = [] }: { snippets?: any[] }) {
  const [activeTab, setActiveTab] = useState<TabType>('sources');
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/status');
        setStatus(await res.json());
      } catch (e) {
        console.error("Status fetch failed", e);
      }
    };
    fetchStatus();
    const int = setInterval(fetchStatus, 5000);
    return () => clearInterval(int);
  }, []);

  const sourceChunks: SourceChunk[] = snippets.map((s, i) => ({
    id: i.toString(),
    fileName: s.source,
    page: 1,
    content: s.text,
    relevance: s.score,
  }));

  const tabs = [
    { id: 'sources' as TabType, label: 'Sources', icon: FileText },
    { id: 'knowledge-graph' as TabType, label: 'Knowledge Graph', icon: Network },
    { id: 'system-status' as TabType, label: 'System Status', icon: Activity },
  ];

  return (
    <div className="w-[300px] h-full bg-card border-l border-border flex flex-col">
      {/* Tabs */}
      <div className="flex border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 px-3 py-3 text-xs font-medium transition-colors relative ${
              activeTab === tab.id
                ? 'text-primary'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <div className="flex items-center justify-center gap-1.5">
              <tab.icon className="w-3.5 h-3.5" />
              <span className="hidden xl:inline">{tab.label}</span>
            </div>
            {activeTab === tab.id && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'sources' && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-foreground mb-3">Retrieved Sources</h3>
            {sourceChunks.map((chunk) => (
              <div
                key={chunk.id}
                className="p-3 rounded-lg bg-muted/30 border border-border hover:border-primary/50 transition-colors cursor-pointer"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                    <span className="text-xs font-medium text-foreground truncate">
                      {chunk.fileName}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground flex-shrink-0">
                    p.{chunk.page}
                  </span>
                </div>
                
                <p className="text-xs text-muted-foreground leading-relaxed line-clamp-4 mb-2">
                  {chunk.content}
                </p>
                
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Relevance:</span>
                  <div className="flex items-center gap-1.5">
                    <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500"
                        style={{ width: `${chunk.relevance * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-green-400">
                      {(chunk.relevance * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'knowledge-graph' && (
          <div className="space-y-4 text-center py-10">
            <div className="w-16 h-16 rounded-2xl bg-primary/5 flex items-center justify-center mx-auto mb-4 border border-primary/10">
              <Network className="w-8 h-8 text-primary opacity-50" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">KG Engine Active</h3>
            <p className="text-xs text-muted-foreground px-6 leading-relaxed">
              The Knowledge Graph is operational and handling entity-based routing for faculty and course queries.
            </p>
          </div>
        )}

        {activeTab === 'system-status' && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-foreground mb-3">System Status</h3>
            
            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <span className="text-xs font-semibold text-green-400">PDFs Indexed</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Total Chunks:</span>
                    <span className="text-foreground font-medium">{status?.chunks || 0}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Documents:</span>
                    <span className="text-foreground font-medium">{status?.pdfs || 0} files</span>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-purple-500" />
                    <span className="text-xs font-semibold text-purple-400">Knowledge Graph</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Status:</span>
                    <span className="text-foreground font-medium">Connected</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Fuseki DB:</span>
                    <span className="text-foreground font-medium">Awaiting Ops</span>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-blue-500" />
                    <span className="text-xs font-semibold text-blue-400">Vector DB {status?.vector_ready ? 'Ready' : 'Off'}</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">FAISS Index:</span>
                    <span className="text-foreground font-medium">{status?.vector_ready ? 'Active' : 'Offline'}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">BM25 Index:</span>
                    <span className="text-foreground font-medium">{status?.vector_ready ? 'Active' : 'Offline'}</span>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <span className="text-xs font-semibold text-green-400">LLM Connected</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Model:</span>
                    <span className="text-foreground font-medium">Llama 3.2</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Provider:</span>
                    <span className="text-foreground font-medium">Ollama (Local)</span>
                  </div>
                </div>
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}