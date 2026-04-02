import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Navbar } from './components/Navbar';
import { LeftSidebar } from './components/LeftSidebar';
import { MessageInputBar } from './components/MessageInputBar';
import { IntelligencePanel } from './components/IntelligencePanel';
import { KnowledgeGraphEditor } from './components/KnowledgeGraphEditor';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  mode?: 'knowledge-graph' | 'hybrid-rag' | 'combined' | 'fallback';
  confidence?: number;
  sources?: Array<{ type: string; reference: string }>;
  reasoning?: {
    intent: string;
    routing: string;
    queryType?: string;
    confidence: number;
    chunksUsed?: number;
  };
  timestamp: string;
}

interface SystemStatus {
  pdfs: number;
  chunks: number;
  vector_ready: boolean;
  kg_ready: boolean;
  llm_provider: string;
  llm_model: string;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [activeSnippets, setActiveSnippets] = useState<any[]>([]);
  const chatAreaRef = useRef<HTMLDivElement>(null);
  const [showKGEditor, setShowKGEditor] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isDark, setIsDark] = useState(() => {
    if (typeof document !== 'undefined') {
      return document.documentElement.classList.contains('dark') || 
             (!document.documentElement.classList.contains('light') && true);
    }
    return true;
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

    const fetchStatus = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/status');
        if (!response.ok) {
          throw new Error('Status request failed');
        }
        const data = await response.json();
        if (active) {
          setSystemStatus(data);
        }
      } catch (error) {
        if (active) {
          setSystemStatus(null);
        }
      }
    };

    fetchStatus();
    const intervalId = window.setInterval(fetchStatus, 5000);
    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const handleSendMessage = async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);
    setActiveSnippets([]);

    // Gather last 4 turns for context
    const history = messages.slice(-4).map(msg => ({
      role: msg.type,
      content: msg.content
    }));

    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: content, history: history }),
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
      const data = await response.json();

      const assistantMessage: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        content: data.answer,
        mode:
          data.mode === 'Knowledge Graph Mode'
            ? 'knowledge-graph'
            : data.mode === 'Combined Mode'
              ? 'combined'
              : data.mode === 'No DB hit'
                ? 'fallback'
                : 'hybrid-rag',
        confidence: data.confidence,
        sources: data.snippets?.map((s: any) => ({
          type: 'Document',
          reference: `${s.source} (${(s.score * 100).toFixed(0)}% match)`
        })) || [],
        reasoning: {
          intent: data.reasoning.match(/Intent Detected: \*\*(.*?)\*\*/)?.[1] || 'GENERAL',
          routing: data.reasoning.match(/Routing: \*\*(.*?)\*\*/)?.[1] || 'Vector Search',
          queryType: data.reasoning.match(/Query Type: \*\*(.*?)\*\*/)?.[1] || 'Standard RAG',
          confidence: (data.confidence || 0) / 100,
          chunksUsed: data.snippets?.length || 0
        },
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      setActiveSnippets(data.snippets || []);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        content: `I could not complete that request.\n\nReason: ${(error as Error).message || 'The backend is unavailable right now.'}\n\nPlease check whether the API, Ollama, and Fuseki services are running.`,
        mode: 'fallback',
        confidence: 0,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-background overflow-hidden relative">
      <Navbar 
        onEditKG={() => setShowKGEditor(true)} 
        isDark={isDark} 
        onToggleTheme={() => setIsDark(!isDark)} 
        status={systemStatus}
      />
      
      {showKGEditor && (
        <KnowledgeGraphEditor onClose={() => setShowKGEditor(false)} />
      )}
      
      <div className="flex-1 flex overflow-hidden">
        <LeftSidebar />
        
        <div className="flex-1 flex flex-col overflow-hidden">
          <div ref={chatAreaRef} className="flex-1 overflow-hidden">
            <ChatAreaWithMessages 
              messages={messages} 
              isTyping={isTyping} 
              onSendMessage={handleSendMessage}
            />
          </div>
          
          <MessageInputBar onSendMessage={handleSendMessage} disabled={isTyping} />
        </div>
        
        <IntelligencePanel snippets={activeSnippets} status={systemStatus} />
      </div>
    </div>
  );
}

// Wrapper component to pass messages to ChatArea
function ChatAreaWithMessages({ 
  messages, 
  isTyping, 
  onSendMessage 
}: { 
  messages: Message[]; 
  isTyping: boolean;
  onSendMessage: (msg: string) => void;
}) {
  const [expandedReasoning, setExpandedReasoning] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const toggleReasoning = (messageId: string) => {
    setExpandedReasoning(prev => prev === messageId ? null : messageId);
  };

  const getModeConfig = (mode?: string) => {
    switch (mode) {
      case 'knowledge-graph':
        return { emoji: 'KG', label: 'Knowledge Graph Mode', color: 'text-emerald-300 bg-emerald-500/10' };
      case 'hybrid-rag':
        return { emoji: 'RAG', label: 'Hybrid RAG Mode', color: 'text-sky-300 bg-sky-500/10' };
      case 'combined':
        return { emoji: 'Mix', label: 'Combined Mode', color: 'text-amber-300 bg-amber-500/10' };
      case 'fallback':
        return { emoji: 'Low', label: 'Low Context Mode', color: 'text-rose-300 bg-rose-500/10' };
      default:
        return { emoji: 'AI', label: 'AI Mode', color: 'text-gray-300 bg-gray-300/10' };
    }
  };

  const SUGGESTED_PROMPTS = [
    "Who teaches Operating Systems?",
    "Explain Module 3 syllabus",
    "What are KTU exam rules?",
  ];

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-6 py-8">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-white flex items-center justify-center mb-6">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="black" fillOpacity="0.9"/>
                <path d="M2 17L12 22L22 17" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-foreground mb-2">
              Welcome to NexRAG AI
            </h2>
            <p className="text-muted-foreground text-center mb-8">
              Hybrid Intelligence for Academic Queries
            </p>
            
            <div className="w-full space-y-3">
              <p className="text-sm text-muted-foreground mb-3">Suggested prompts:</p>
              {SUGGESTED_PROMPTS.map((prompt, index) => (
                <button
                  key={index}
                  onClick={() => onSendMessage(prompt)}
                  className="w-full p-4 rounded-xl bg-card border border-border hover:border-primary/50 text-left transition-all hover:shadow-lg hover:shadow-primary/10 group"
                >
                  <p className="text-sm text-foreground group-hover:text-primary transition-colors">
                    {prompt}
                  </p>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((message) => (
              <MessageBubble 
                key={message.id} 
                message={message}
                expandedReasoning={expandedReasoning}
                toggleReasoning={toggleReasoning}
                getModeConfig={getModeConfig}
              />
            ))}
            
            {isTyping && (
              <TypingIndicator />
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ 
  message, 
  expandedReasoning, 
  toggleReasoning, 
  getModeConfig 
}: { 
  message: Message;
  expandedReasoning: string | null;
  toggleReasoning: (id: string) => void;
  getModeConfig: (mode?: string) => { emoji: string; label: string; color: string };
}) {
  return (
    <div className={`flex gap-4 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
      {message.type === 'assistant' && (
        <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center flex-shrink-0">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="black" fillOpacity="0.9"/>
            <path d="M2 17L12 22L22 17" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M2 12L12 17L22 12" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      )}
      
      <div className={`flex-1 max-w-[85%] ${message.type === 'user' ? 'flex justify-end' : ''}`}>
        <div className={`rounded-2xl p-4 ${
          message.type === 'user' 
            ? 'bg-white text-black ml-auto' 
            : 'bg-card border border-border'
        }`}>
          {message.type === 'assistant' && message.mode && (
            <div className="mb-3">
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium ${getModeConfig(message.mode).color}`}>
                <span>{getModeConfig(message.mode).emoji}</span>
                {getModeConfig(message.mode).label}
              </span>
            </div>
          )}
          
          <div className={`text-sm leading-relaxed ${message.type === 'user' ? 'text-black' : 'text-foreground'}`}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({node, ...props}) => <p className="mb-3 last:mb-0" {...props} />,
                ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-3 space-y-1" {...props} />,
                ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-3 space-y-1" {...props} />,
                li: ({node, ...props}) => <li className="leading-relaxed" {...props} />,
                strong: ({node, ...props}) => <strong className="font-semibold" {...props} />,
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
          
          {message.type === 'assistant' && message.confidence !== undefined && (
            <div className="mt-4 pt-4 border-t border-border/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Confidence:</span>
                <span className={`text-xs font-semibold ${
                  message.confidence >= 85 ? 'text-green-400' : message.confidence >= 60 ? 'text-amber-400' : 'text-rose-400'
                }`}>
                  {message.confidence}%
                </span>
              </div>
              
              {message.sources && message.sources.length > 0 && (
                <div className="mt-2">
                  <span className="text-xs text-muted-foreground block mb-1.5">Sources:</span>
                  <div className="space-y-1">
                    {message.sources.map((source, idx) => (
                      <div key={idx} className="text-xs text-foreground flex items-start gap-1.5">
                        <span className="text-primary">-</span>
                        <span className="font-medium">{source.type}:</span>
                        <span className="text-muted-foreground">{source.reference}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          
          {message.type === 'assistant' && message.reasoning && (
            <ReasoningPanel 
              message={message}
              isExpanded={expandedReasoning === message.id}
              onToggle={() => toggleReasoning(message.id)}
            />
          )}
        </div>
      </div>
      
      {message.type === 'user' && (
        <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center flex-shrink-0">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="8" r="4" fill="currentColor"/>
            <path d="M6 21C6 17.134 8.686 14 12 14C15.314 14 18 17.134 18 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>
      )}
    </div>
  );
}

function ReasoningPanel({ 
  message, 
  isExpanded, 
  onToggle 
}: { 
  message: Message;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="mt-3">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
      >
        <span className="text-xs font-medium text-foreground">AI Reasoning</span>
        {isExpanded ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M18 15L12 9L6 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M6 9L12 15L18 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        )}
      </button>
      
      {isExpanded && message.reasoning && (
        <div className="mt-2 p-3 rounded-lg bg-muted/20 border border-border/50 space-y-1.5">
          <div className="flex justify-between">
            <span className="text-xs text-muted-foreground">Intent:</span>
            <span className="text-xs font-mono text-foreground">{message.reasoning.intent}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-xs text-muted-foreground">Routing:</span>
            <span className="text-xs font-mono text-foreground">{message.reasoning.routing}</span>
          </div>
          {message.reasoning.queryType && (
            <div className="flex justify-between">
              <span className="text-xs text-muted-foreground">Query Type:</span>
              <span className="text-xs font-mono text-foreground">{message.reasoning.queryType}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-xs text-muted-foreground">Confidence:</span>
            <span className="text-xs font-mono text-green-400">{message.reasoning.confidence.toFixed(2)}</span>
          </div>
          {message.reasoning.chunksUsed !== undefined && (
            <div className="flex justify-between">
              <span className="text-xs text-muted-foreground">Chunks Used:</span>
              <span className="text-xs font-mono text-foreground">{message.reasoning.chunksUsed}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-4 justify-start">
      <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center flex-shrink-0">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="black" fillOpacity="0.9"/>
          <path d="M2 17L12 22L22 17" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M2 12L12 17L22 12" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <div className="bg-card border border-border rounded-2xl p-4">
        <div className="flex gap-1.5">
          <div className="w-2 h-2 rounded-full bg-primary animate-typing"></div>
          <div className="w-2 h-2 rounded-full bg-primary animate-typing" style={{ animationDelay: '0.2s' }}></div>
          <div className="w-2 h-2 rounded-full bg-primary animate-typing" style={{ animationDelay: '0.4s' }}></div>
        </div>
      </div>
    </div>
  );
}

export default App;
