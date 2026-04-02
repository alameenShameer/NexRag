import { FileText, Network, Activity, CheckCircle2 } from 'lucide-react';
import { useState } from 'react';

type TabType = 'sources' | 'knowledge-graph' | 'system-status';

interface SourceChunk {
  id: string;
  fileName: string;
  page: number;
  content: string;
  relevance: number;
}

export function IntelligencePanel() {
  const [activeTab, setActiveTab] = useState<TabType>('sources');

  const sourceChunks: SourceChunk[] = [
    {
      id: '1',
      fileName: 'Syllabus_CS302.pdf',
      page: 18,
      content: 'Module 3: Process Synchronization - Critical Section Problem, Peterson\'s Solution, Semaphores, Classical Synchronization Problems including Producer-Consumer, Readers-Writers, and Dining Philosophers...',
      relevance: 0.94,
    },
    {
      id: '2',
      fileName: 'Faculty_Database.pdf',
      page: 3,
      content: 'Dr. Alan Mathew - Assistant Professor, Computer Science Department. Specialization: Operating Systems, Distributed Systems. Experience: 8 years. Courses: CS302 (Operating Systems), CS401 (Advanced OS)...',
      relevance: 0.91,
    },
    {
      id: '3',
      fileName: 'KTU_Guidelines.pdf',
      page: 7,
      content: 'Examination Rules: Students must maintain minimum 75% attendance. Internal assessment: 40 marks (20 for tests, 10 for assignments, 10 for seminar). End semester: 60 marks. Pass mark: 50% overall...',
      relevance: 0.88,
    },
  ];

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
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-foreground mb-3">Knowledge Graph</h3>
            
            {/* Graph Data - Text-based */}
            <div className="space-y-2">
              <div className="p-3 rounded-lg bg-muted/30 border border-border">
                <h4 className="text-xs font-semibold text-foreground mb-2">Entities</h4>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Courses:</span>
                    <span className="text-xs font-medium text-foreground">247</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Faculty:</span>
                    <span className="text-xs font-medium text-foreground">89</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Departments:</span>
                    <span className="text-xs font-medium text-foreground">12</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Rules:</span>
                    <span className="text-xs font-medium text-foreground">156</span>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-muted/30 border border-border">
                <h4 className="text-xs font-semibold text-foreground mb-2">Relationships</h4>
                <div className="space-y-1.5">
                  <div className="text-xs">
                    <span className="text-foreground font-medium">CS302</span>
                    <span className="text-muted-foreground mx-1">→</span>
                    <span className="text-muted-foreground">taught by</span>
                    <span className="text-muted-foreground mx-1">→</span>
                    <span className="text-foreground font-medium">Dr. Alan Mathew</span>
                  </div>
                  <div className="text-xs">
                    <span className="text-foreground font-medium">CS302</span>
                    <span className="text-muted-foreground mx-1">→</span>
                    <span className="text-muted-foreground">belongs to</span>
                    <span className="text-muted-foreground mx-1">→</span>
                    <span className="text-foreground font-medium">CS Department</span>
                  </div>
                  <div className="text-xs">
                    <span className="text-foreground font-medium">CS302</span>
                    <span className="text-muted-foreground mx-1">→</span>
                    <span className="text-muted-foreground">requires</span>
                    <span className="text-muted-foreground mx-1">→</span>
                    <span className="text-foreground font-medium">Mathematics</span>
                  </div>
                  <div className="text-xs">
                    <span className="text-foreground font-medium">Dr. Alan</span>
                    <span className="text-muted-foreground mx-1">→</span>
                    <span className="text-muted-foreground">specializes in</span>
                    <span className="text-muted-foreground mx-1">→</span>
                    <span className="text-foreground font-medium">Systems</span>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-muted/30 border border-border">
                <h4 className="text-xs font-semibold text-foreground mb-2">Graph Metrics</h4>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Avg Connections:</span>
                    <span className="text-xs font-medium text-foreground">3.12</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Graph Density:</span>
                    <span className="text-xs font-medium text-foreground">0.68</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Connected Components:</span>
                    <span className="text-xs font-medium text-foreground">1</span>
                  </div>
                </div>
              </div>
            </div>
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
                    <span className="text-foreground font-medium">1,847</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Documents:</span>
                    <span className="text-foreground font-medium">3 files</span>
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
                    <span className="text-muted-foreground">Nodes:</span>
                    <span className="text-foreground font-medium">1,247</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Edges:</span>
                    <span className="text-foreground font-medium">3,891</span>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-blue-500" />
                    <span className="text-xs font-semibold text-blue-400">Vector DB Ready</span>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">FAISS Index:</span>
                    <span className="text-foreground font-medium">Active</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">BM25 Index:</span>
                    <span className="text-foreground font-medium">Active</span>
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
                    <span className="text-foreground font-medium">Mistral 7B</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Provider:</span>
                    <span className="text-foreground font-medium">Ollama (Local)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="mt-4 pt-4 border-t border-border">
              <h4 className="text-xs font-semibold text-foreground mb-2">Performance</h4>
              <div className="space-y-2">
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-muted-foreground">Avg Response Time:</span>
                    <span className="text-foreground font-medium">1.2s</span>
                  </div>
                  <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-green-500" style={{ width: '85%' }}></div>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-muted-foreground">System Load:</span>
                    <span className="text-foreground font-medium">42%</span>
                  </div>
                  <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500" style={{ width: '42%' }}></div>
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