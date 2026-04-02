import { useState, useRef, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { LeftSidebar } from './components/LeftSidebar';
import { ChatArea } from './components/ChatArea';
import { MessageInputBar } from './components/MessageInputBar';
import { IntelligencePanel } from './components/IntelligencePanel';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  mode?: 'knowledge-graph' | 'hybrid-rag' | 'combined';
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

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const chatAreaRef = useRef<HTMLDivElement>(null);

  const handleSendMessage = (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsTyping(true);

    // Simulate AI response
    setTimeout(() => {
      setIsTyping(false);
      const mockResponse = generateMockResponse(content);
      setMessages(prev => [...prev, mockResponse]);
    }, 2000);
  };

  const generateMockResponse = (query: string): Message => {
    const queryLower = query.toLowerCase();
    
    if (queryLower.includes('teach') || queryLower.includes('faculty') || queryLower.includes('professor')) {
      return {
        id: Date.now().toString(),
        type: 'assistant',
        content: 'Operating Systems (CS302) is taught by **Dr. Alan Mathew**, Assistant Professor in the Computer Science Department. He has 8 years of teaching experience and specializes in system programming and distributed systems.',
        mode: 'knowledge-graph',
        confidence: 98,
        sources: [
          { type: 'Knowledge Graph', reference: 'Faculty Database' },
          { type: 'Document', reference: 'Page 3 (Faculty_List.pdf)' },
        ],
        reasoning: {
          intent: 'FACULTY_QUERY',
          routing: 'Knowledge Graph',
          queryType: 'SPARQL Query Used',
          confidence: 0.98,
        },
        timestamp: new Date().toISOString(),
      };
    } else if (queryLower.includes('module') || queryLower.includes('syllabus')) {
      return {
        id: Date.now().toString(),
        type: 'assistant',
        content: 'Module 3 covers **Process Synchronization and Deadlocks**. Key topics include: Critical Section Problem, Peterson\'s Solution, Semaphores, Classical Synchronization Problems (Producer-Consumer, Readers-Writers, Dining Philosophers), and Deadlock Prevention/Avoidance strategies.',
        mode: 'hybrid-rag',
        confidence: 94,
        sources: [
          { type: 'Document', reference: 'Page 18-24 (Syllabus_CS302.pdf)' },
          { type: 'Retrieval', reference: 'FAISS + BM25 (3 chunks)' },
        ],
        reasoning: {
          intent: 'SYLLABUS_QUERY',
          routing: 'Hybrid RAG',
          queryType: 'Reranked by CrossEncoder',
          confidence: 0.94,
          chunksUsed: 3,
        },
        timestamp: new Date().toISOString(),
      };
    } else if (queryLower.includes('rule') || queryLower.includes('exam') || queryLower.includes('ktu')) {
      return {
        id: Date.now().toString(),
        type: 'assistant',
        content: 'KTU examination rules state: Students must maintain **75% attendance** to be eligible for exams. The internal assessment carries 40 marks (20 for tests, 10 for assignments, 10 for seminar). End semester exam is for 60 marks with a minimum pass mark of 50% overall.',
        mode: 'combined',
        confidence: 91,
        sources: [
          { type: 'Document', reference: 'Page 7-9 (KTU_Guidelines.pdf)' },
          { type: 'Knowledge Graph', reference: 'Rules Database' },
          { type: 'Retrieval', reference: 'Hybrid Search (2 chunks)' },
        ],
        reasoning: {
          intent: 'REGULATION_QUERY',
          routing: 'Combined Mode (KG + RAG)',
          queryType: 'Multi-source fusion',
          confidence: 0.91,
          chunksUsed: 2,
        },
        timestamp: new Date().toISOString(),
      };
    } else {
      return {
        id: Date.now().toString(),
        type: 'assistant',
        content: 'I can help you with questions about faculty information, course syllabi, KTU regulations, and academic queries. Please try asking about specific courses, professors, or university rules.',
        mode: 'hybrid-rag',
        confidence: 85,
        sources: [
          { type: 'General', reference: 'System Knowledge' },
        ],
        reasoning: {
          intent: 'GENERAL_QUERY',
          routing: 'Fallback Response',
          confidence: 0.85,
        },
        timestamp: new Date().toISOString(),
      };
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-background overflow-hidden">
      <Navbar />
      
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
          
          <MessageInputBar onSendMessage={handleSendMessage} />
        </div>
        
        <IntelligencePanel />
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
        return { emoji: '⚫', label: 'Knowledge Graph Mode', color: 'text-white bg-white/10' };
      case 'hybrid-rag':
        return { emoji: '⚪', label: 'Hybrid RAG Mode', color: 'text-gray-300 bg-gray-300/10' };
      case 'combined':
        return { emoji: '◐', label: 'Combined Mode', color: 'text-gray-400 bg-gray-400/10' };
      default:
        return { emoji: '⚪', label: 'AI Mode', color: 'text-gray-300 bg-gray-300/10' };
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
          
          <p className={`text-sm leading-relaxed ${message.type === 'user' ? 'text-black' : 'text-foreground'}`}>
            {message.content}
          </p>
          
          {message.type === 'assistant' && message.confidence && (
            <div className="mt-4 pt-4 border-t border-border/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Confidence:</span>
                <span className="text-xs font-semibold text-green-400">{message.confidence}%</span>
              </div>
              
              {message.sources && message.sources.length > 0 && (
                <div className="mt-2">
                  <span className="text-xs text-muted-foreground block mb-1.5">Sources:</span>
                  <div className="space-y-1">
                    {message.sources.map((source, idx) => (
                      <div key={idx} className="text-xs text-foreground flex items-start gap-1.5">
                        <span className="text-primary">•</span>
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
          {message.reasoning.chunksUsed && (
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