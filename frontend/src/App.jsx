import React, { useState, useEffect, useRef } from 'react';
import './index.css';

const API_URL = 'http://127.0.0.1:8000/api';

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [status, setStatus] = useState(null);
  const [tab, setTab] = useState('Sources');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/status`);
      setStatus(await res.json());
    } catch(e) { console.error('API Error', e); }
  };

  useEffect(() => {
    fetchStatus();
    const int = setInterval(fetchStatus, 5000);
    return () => clearInterval(int);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (question) => {
    if (!question.trim()) return;
    const userMsg = { role: 'user', content: question };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: question })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', ...data }]);
    } catch(e) {
      setMessages(prev => [...prev, { role: 'assistant', answer: 'Connection error to FastAPI.', mode: 'Error' }]);
    }
    setLoading(false);
  };

  const handleUpload = async (e) => {
    if(!e.target.files?.length) return;
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', 'General');
    try {
      await fetch(`${API_URL}/upload`, { method: 'POST', body: formData });
      fetchStatus();
    } catch(e) { alert('Upload failed'); }
  };

  return (
    <div className="app-container">
      {/* LEFT SIDEBAR */}
      <div className="sidebar">
        <div>
          <h2 style={{margin: '0 0 4px 0'}}>🧠 NexRAG AI</h2>
          <div className="text-gray" style={{fontSize: 12}}>Hybrid Intelligence for Academic Queries</div>
        </div>
        <div className="divider" />
        
        <div>
          <div className="header">Upload Documents</div>
          <label className="upload-zone" style={{display:'block', marginTop:12}}>
            <input type="file" style={{display:'none'}} accept=".pdf" onChange={handleUpload} />
            <div style={{fontWeight:600}}>📥 Click or Drop PDF</div>
            <div className="text-gray" style={{fontSize:12, marginTop:4}}>Updates internal Vector DB instantly</div>
          </label>
        </div>

        <div>
          <div className="header">Documents ({status?.pdfs || 0})</div>
          <div className="card" style={{marginTop:12}}>
             <div className="text-gray" style={{fontSize:13}}>Monitored from backend vault</div>
             {status?.chunks > 0 && <div className="text-green mt-2" style={{marginTop:8, fontSize:12, fontWeight:600}}>✓ {status.chunks} Chunks Embedded</div>}
          </div>
        </div>
      </div>

      {/* CENTER CHAT */}
      <div className="main-chat">
        <div className="chat-window">
          {messages.length === 0 ? (
            <div style={{margin: 'auto', maxWidth: 600, width: '100%', paddingBottom: 60}}>
              <h1 style={{textAlign:'center', marginBottom: 8, fontSize: 32}}>Welcome to NexRAG AI</h1>
              <p style={{textAlign:'center', color:'#888899', marginBottom: 40, fontSize: 16}}>FastAPI + React Production Interface</p>
              
              <div style={{display:'flex', flexDirection:'column', gap: 16}}>
                <button className="suggested" onClick={() => handleSend("Who teaches Operating Systems?")}>Who teaches Operating Systems?</button>
                <button className="suggested" onClick={() => handleSend("Explain Module 3 syllabus")}>Explain Module 3 syllabus</button>
                <button className="suggested" onClick={() => handleSend("What are KTU exam rules?")}>What are KTU exam rules?</button>
              </div>
            </div>
          ) : (
            messages.map((m, i) => (
              m.role === 'user' ? (
                <div key={i} className="msg-user">{m.content}</div>
              ) : (
                <div key={i} className="msg-ai">
                  <div style={{display:'flex', justifyContent:'space-between', marginBottom: 20}}>
                    <div style={{fontWeight:600, fontSize:14}}>{m.mode}</div>
                    <div className="text-green" style={{fontWeight:'bold', fontSize:14}}>Confidence: {m.confidence}%</div>
                  </div>
                  <div style={{whiteSpace:'pre-wrap'}}>{m.answer}</div>
                </div>
              )
            ))
          )}
          {loading && <div className="msg-ai" style={{width:'fit-content'}}>Thinking...</div>}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-wrapper">
          <input 
            type="text" 
            className="chat-input"
            placeholder="Ask anything about your college..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSend(input); }}
          />
        </div>
      </div>

      {/* RIGHT SIDEBAR */}
      <div className="sidebar" style={{borderLeft: '1px solid #333344'}}>
        <div className="tabs">
          <div className={`tab ${tab==='Sources'?'active':''}`} onClick={()=>setTab('Sources')}>Sources</div>
          <div className={`tab ${tab==='Status'?'active':''}`} onClick={()=>setTab('Status')}>Status</div>
        </div>

        {tab === 'Status' && (
          <div style={{display:'flex', flexDirection:'column', gap: 16}}>
            <div className="card" style={{borderLeft: '4px solid #4ade80'}}>
               <div style={{color:'#4ade80', fontWeight:'bold', marginBottom:8}}>● PDFs Indexed</div>
               <div className="text-gray" style={{fontSize:13}}>Total Files: {status?.pdfs || 0}</div>
               <div className="text-gray" style={{fontSize:13}}>Vector Chunks: {status?.chunks || 0}</div>
            </div>
            {status?.vector_ready ? (
              <div className="card" style={{borderLeft: '4px solid #facc15'}}>
                <div style={{color:'#facc15', fontWeight:'bold', marginBottom:4}}>● Vector DB Active</div>
                <div className="text-gray" style={{fontSize:12}}>Local FAISS Memory Loaded</div>
              </div>
            ) : (
              <div className="card" style={{borderLeft: '4px solid #ef4444'}}>
                <div style={{color:'#ef4444', fontWeight:'bold'}}>○ Vector DB Off</div>
              </div>
            )}
            <div className="card" style={{borderLeft: '4px solid #60a5fa'}}>
               <div style={{color:'#60a5fa', fontWeight:'bold', marginBottom:4}}>● LLM Connected</div>
               <div className="text-gray" style={{fontSize:13}}>Ollama backend (Mistral) via Python RAG engine</div>
            </div>
          </div>
        )}

        {tab === 'Sources' && (
          <div>
            <div className="header" style={{marginBottom:16}}>Retrieved Context</div>
            {(messages.filter(m => m.role === 'assistant').pop()?.snippets || []).map((snip, i) => (
               <div key={i} className="card" style={{marginBottom:16}}>
                 <div style={{display:'flex', justifyContent:'space-between', marginBottom:8}}>
                   <div style={{fontSize:13, fontWeight:600, color:'#e5e7eb', wordBreak:'break-all'}}>{snip.source}</div>
                   <div className="text-green" style={{fontSize:12}}>Score: {snip.score?.toFixed(2)}</div>
                 </div>
                 <div className="text-gray" style={{fontSize:13, fontStyle:'italic'}}>{snip.text}...</div>
               </div>
            ))}
            {messages.length > 0 && !(messages.filter(m => m.role === 'assistant').pop()?.snippets?.length) && (
               <div className="text-gray" style={{fontSize:13}}>No vector sources retrieved.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
