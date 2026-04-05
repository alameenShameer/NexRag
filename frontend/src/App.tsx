import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Toaster } from 'sonner';
import { Navbar } from './components/Navbar';
import { LeftSidebar } from './components/LeftSidebar';
import { MessageInputBar } from './components/MessageInputBar';
import { KnowledgeBasePanel } from './components/KnowledgeBasePanel';
import { BrandMark } from './components/BrandMark';
import { GraphViewDrawer } from './components/GraphViewDrawer';
import { SourcesAccordion } from './components/SourcesAccordion';
import { IntelligencePanel } from './components/IntelligencePanel';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  responseType?: 'fact' | 'definition' | 'explanation';
  status?: 'complete' | 'limited' | 'refused';
  confidence?: number;
  confidenceLabel?: 'High' | 'Medium' | 'Low';
  sources?: Array<{
    title: string;
    page?: number | null;
    excerpt: string;
    score: number;
    match_type: string;
    source_type: string;
    source_url?: string | null;
  }>;
  kgFacts?: Array<{ entity: string; fact: string; score: number }>;
  graphView?: { nodes?: Array<any>; edges?: Array<any> };
  traceId?: string;
  queryPlan?: any;
  sourceGroups?: { documents?: Array<any>; kg_facts?: Array<any> };
  stageLabel?: string;
  timestamp: string;
}

interface ReadinessSnapshot {
  state: 'loading' | 'ready' | 'error';
  message: string;
  pdfs: number;
  official_documents?: number;
  documents_indexed?: number;
  uploads_in_progress?: number;
  chunks: number;
  vector_ready: boolean;
  kg_ready: boolean;
  llm_provider: string;
  llm_model: string;
  active_job?: { run_id?: number; started_at?: string } | null;
  last_refresh_at?: string | null;
  index_version?: string;
  last_error?: string | null;
  checks?: Record<string, { ok: boolean; label: string; detail: string }>;
}

interface HistoryEntry {
  id: string;
  question: string;
  answer: string;
  timestamp: string;
  intent?: string;
}

function mapApiMessage(data: any): Message {
  return {
    id: Date.now().toString(),
    type: 'assistant',
    content: data.answer,
    status: data.status,
    confidence: data.confidence,
    confidenceLabel: data.confidence_label,
    responseType: data.type || 'definition',
    sources: data.sources || [],
    kgFacts: data.kg_facts || [],
    graphView: data.graph_view || { nodes: [], edges: [] },
    traceId: data.trace_id,
    queryPlan: data.query_plan,
    sourceGroups: data.source_groups || { documents: data.sources || [], kg_facts: data.kg_facts || [] },
    timestamp: new Date().toISOString(),
  };
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [showKnowledgeBase, setShowKnowledgeBase] = useState(false);
  const [graphDrawer, setGraphDrawer] = useState<{ title: string; graphView: { nodes?: Array<any>; edges?: Array<any> } } | null>(null);
  const [readiness, setReadiness] = useState<ReadinessSnapshot | null>(null);
  const [isDark, setIsDark] = useState(() => {
    if (typeof document !== 'undefined') {
      return document.documentElement.classList.contains('dark');
    }
    return false;
  });

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    }
  }, [isDark]);

  useEffect(() => {
    let active = true;

    const fetchReadiness = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/readiness');
        if (!response.ok) {
          throw new Error('Readiness request failed');
        }
        const data = await response.json();
        if (active) {
          setReadiness(data);
        }
      } catch (error) {
        if (active) {
          setReadiness({
            state: 'error',
            message: 'Backend status unavailable.',
            pdfs: 0,
            official_documents: 0,
            documents_indexed: 0,
            uploads_in_progress: 0,
            chunks: 0,
            vector_ready: false,
            kg_ready: false,
            llm_provider: 'unknown',
            llm_model: 'unknown',
            last_error: (error as Error).message,
          });
        }
      }
    };

    fetchReadiness();
    const intervalId = window.setInterval(fetchReadiness, 5000);
    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const handleSendMessage = async (content: string) => {
    if (readiness?.state !== 'ready') {
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    const assistantId = `${Date.now()}-assistant`;
    const placeholderAssistant: Message = {
      id: assistantId,
      type: 'assistant',
      content: '',
      responseType: 'definition',
      status: 'limited',
      stageLabel: 'Retrieving documents...',
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage, placeholderAssistant]);
    setIsTyping(true);

    const history = messages.slice(-4).map((msg) => ({
      role: msg.type,
      content: msg.content,
    }));

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: content, history }),
      });

      if (!response.ok) {
        let detail = 'API Error';
        try {
          const errorPayload = await response.json();
          detail = errorPayload.detail || errorPayload.error || detail;
        } catch {
          // Ignore JSON parse failure and use fallback text.
        }
        throw new Error(detail);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      if (!reader) {
        throw new Error('Streaming is unavailable right now.');
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const event of events) {
          const line = event.split('\n').find((part) => part.startsWith('data: '));
          if (!line) {
            continue;
          }

          const payload = JSON.parse(line.slice(6));
          if (payload.type === 'stage') {
            setMessages((prev) => prev.map((message) => (
              message.id === assistantId
                ? { ...message, stageLabel: payload.label }
                : message
            )));
          }

          if (payload.type === 'chunk') {
            setMessages((prev) => prev.map((message) => (
              message.id === assistantId
                ? { ...message, content: `${message.content}${payload.content}` }
                : message
            )));
          }

          if (payload.type === 'done') {
            const finalMessage = {
              ...mapApiMessage(payload.payload),
              id: assistantId,
              stageLabel: undefined,
            };
            setMessages((prev) => prev.map((message) => (
              message.id === assistantId ? finalMessage : message
            )));
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages((prev) => prev.map((message) => (
        message.id === assistantId
          ? {
              ...message,
              content: `I could not complete that request.\n\nReason: ${(error as Error).message || 'The backend is unavailable right now.'}\n\nPlease check whether the API, Ollama, and Fuseki services are running.`,
              responseType: 'definition',
              status: 'refused',
              confidence: 0,
              confidenceLabel: 'Low',
              stageLabel: undefined,
            }
          : message
      )));
    } finally {
      setIsTyping(false);
    }
  };

  const handleOpenHistoryEntry = (entry: HistoryEntry) => {
    setMessages([
      {
        id: `${entry.id}-user`,
        type: 'user',
        content: entry.question,
        timestamp: entry.timestamp || new Date().toISOString(),
      },
      {
        id: `${entry.id}-assistant`,
        type: 'assistant',
        content: entry.answer,
        timestamp: entry.timestamp || new Date().toISOString(),
      },
    ]);
  };

  const latestEvidenceMessage = [...messages].reverse().find(
    (message) => message.type === 'assistant' && ((message.sources?.length || 0) > 0 || (message.kgFacts?.length || 0) > 0),
  );

  return (
    <div className="h-screen w-screen flex flex-col bg-background overflow-hidden relative">
      <Navbar
        onEditKG={() => setShowKnowledgeBase(true)}
        isDark={isDark}
        onToggleTheme={() => setIsDark(!isDark)}
        status={readiness}
      />

      {showKnowledgeBase && (
        <KnowledgeBasePanel onClose={() => setShowKnowledgeBase(false)} />
      )}

      <GraphViewDrawer
        open={graphDrawer !== null}
        onClose={() => setGraphDrawer(null)}
        graphView={graphDrawer?.graphView}
        title={graphDrawer?.title}
      />

      <div className="flex-1 flex overflow-hidden">
        <LeftSidebar onOpenHistoryEntry={handleOpenHistoryEntry} />

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <ChatAreaWithMessages
              messages={messages}
              isTyping={isTyping}
              onSendMessage={handleSendMessage}
              onOpenGraph={(message) => setGraphDrawer({ title: message.content.slice(0, 72) || 'Answer graph', graphView: message.graphView || { nodes: [], edges: [] } })}
              isDark={isDark}
              readiness={readiness}
            />
          </div>

          <MessageInputBar
            onSendMessage={handleSendMessage}
            disabled={isTyping}
            ready={readiness?.state === 'ready'}
            uploadsInProgress={readiness?.uploads_in_progress || 0}
          />
        </div>

        <div className="hidden xl:flex">
          <IntelligencePanel
            sources={latestEvidenceMessage?.sources || []}
            kgFacts={latestEvidenceMessage?.kgFacts || []}
            status={readiness}
          />
        </div>
      </div>
      <Toaster richColors position="top-right" />
    </div>
  );
}

function ChatAreaWithMessages({
  messages,
  isTyping,
  onSendMessage,
  onOpenGraph,
  isDark,
  readiness,
}: {
  messages: Message[];
  isTyping: boolean;
  onSendMessage: (msg: string) => void;
  onOpenGraph: (message: Message) => void;
  isDark: boolean;
  readiness: ReadinessSnapshot | null;
}) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const suggestedPrompts = [
    'Who is the HOD of Computer Science & Engineering?',
    'What is NeuroNest?',
    'Explain the placement process.',
  ];

  const isReady = readiness?.state === 'ready';

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-6 py-8">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto">
            <BrandMark size={64} rounded="rounded-2xl" className="mb-6" theme={isDark ? 'dark' : 'light'} />
            <h2 className="text-2xl font-semibold text-foreground mb-2">Welcome to NexRag</h2>
            <p className="text-muted-foreground text-center mb-8">Hybrid Intelligence for Academic Queries</p>

            {!isReady ? (
              <div className={`w-full rounded-2xl border p-6 ${readiness?.state === 'error' ? 'border-rose-500/30 bg-rose-500/10' : 'border-border bg-card'}`}>
                <p className="text-sm font-medium text-foreground">
                  {readiness?.message || 'Initializing backend / Indexing documents...'}
                </p>
                <div className="mt-4 space-y-2">
                  {Object.values(readiness?.checks || {}).map((check) => (
                    <div key={check.label} className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">{check.label}</span>
                      <span className={check.ok ? 'text-emerald-400' : 'text-amber-400'}>{check.detail}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="w-full space-y-3">
                <p className="text-sm text-muted-foreground mb-3">Suggested prompts:</p>
                {suggestedPrompts.map((prompt, index) => (
                  <button
                    key={index}
                    onClick={() => onSendMessage(prompt)}
                    className="w-full p-4 rounded-xl bg-card border border-border hover:border-primary/50 text-left transition-all hover:shadow-lg hover:shadow-primary/10 group"
                  >
                    <p className="text-sm text-foreground group-hover:text-primary transition-colors">{prompt}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onOpenGraph={onOpenGraph}
                isDark={isDark}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  onOpenGraph,
  isDark,
}: {
  message: Message;
  onOpenGraph: (message: Message) => void;
  isDark: boolean;
}) {
  const evidenceBadge = (() => {
    if (message.status === 'limited') {
      return { label: 'Limited Evidence', color: 'text-amber-300 bg-amber-500/10' };
    }
    if (message.status === 'refused') {
      return { label: 'No Evidence', color: 'text-rose-300 bg-rose-500/10' };
    }
    if (message.confidenceLabel === 'High') {
      return { label: 'High Confidence', color: 'text-emerald-300 bg-emerald-500/10' };
    }
    if (message.confidenceLabel === 'Medium') {
      return { label: 'Medium Confidence', color: 'text-sky-300 bg-sky-500/10' };
    }
    return { label: 'Assistant', color: 'text-gray-300 bg-gray-300/10' };
  })();
  const typeBadgeLabel =
    message.responseType === 'fact'
      ? 'Fact'
      : message.responseType === 'explanation'
        ? 'Explanation'
        : message.responseType === 'definition'
          ? 'Definition'
          : null;

  return (
    <div className={`flex gap-4 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
      {message.type === 'assistant' && (
        <BrandMark size={32} rounded="rounded-lg" className="flex-shrink-0" theme={isDark ? 'dark' : 'light'} />
      )}

      <div className={`flex-1 max-w-[85%] ${message.type === 'user' ? 'flex justify-end' : ''}`}>
        <div className={`rounded-2xl p-4 ${
          message.type === 'user'
            ? 'bg-white text-black ml-auto'
            : 'bg-card border border-border'
        }`}>
          {message.type === 'assistant' && (
            <div className="mb-3 flex flex-wrap gap-2">
              <span className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium ${evidenceBadge.color}`}>
                {evidenceBadge.label}
              </span>
              {typeBadgeLabel ? (
                <span className="inline-flex items-center rounded-lg bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
                  Type: {typeBadgeLabel}
                </span>
              ) : null}
              {message.stageLabel ? (
                <span className="inline-flex items-center rounded-lg bg-muted px-2.5 py-1 text-xs font-medium text-primary">
                  {message.stageLabel}
                </span>
              ) : null}
            </div>
          )}

          <div className={`text-sm leading-relaxed ${message.type === 'user' ? 'text-black' : 'text-foreground'}`}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ node, ...props }) => <p className="mb-3 last:mb-0" {...props} />,
                ul: ({ node, ...props }) => <ul className="list-disc pl-5 mb-3 space-y-1" {...props} />,
                ol: ({ node, ...props }) => <ol className="list-decimal pl-5 mb-3 space-y-1" {...props} />,
                li: ({ node, ...props }) => <li className="leading-relaxed" {...props} />,
                strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
              }}
            >
              {message.content || (message.stageLabel ? '' : 'Preparing response...')}
            </ReactMarkdown>
          </div>

          {message.type === 'assistant' && message.confidence !== undefined && (
            <div className="mt-4 pt-4 border-t border-border/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Confidence:</span>
                <span className={`text-xs font-semibold ${
                  message.confidence >= 0.8 ? 'text-green-400' : message.confidence >= 0.5 ? 'text-amber-400' : 'text-rose-400'
                }`}>
                  {Math.round(message.confidence * 100)}%
                </span>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {(message.sources?.length || message.kgFacts?.length) ? (
                  <span className="rounded-full border border-border bg-muted/30 px-2.5 py-1 text-[11px] text-muted-foreground">
                    {message.sources?.length || 0} sources • {message.kgFacts?.length || 0} graph facts
                  </span>
                ) : null}
                {(message.graphView?.nodes?.length || message.graphView?.edges?.length) ? (
                  <button
                    type="button"
                    onClick={() => onOpenGraph(message)}
                    className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary transition-colors hover:bg-primary/20"
                  >
                    Knowledge Graph View
                  </button>
                ) : null}
              </div>

              <div className="xl:hidden">
                <SourcesAccordion sources={message.sources} kgFacts={message.kgFacts} />
              </div>
            </div>
          )}
        </div>
      </div>

      {message.type === 'user' && (
        <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center flex-shrink-0">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="8" r="4" fill="currentColor" />
            <path d="M6 21C6 17.134 8.686 14 12 14C15.314 14 18 17.134 18 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>
      )}
    </div>
  );
}

export default App;
