import { Upload, FileText, CheckCircle2, Clock, Network, History } from 'lucide-react';
import { useState, useEffect } from 'react';

interface Document {
  id: string;
  name: string;
  status: 'uploading' | 'processing' | 'completed';
  pages?: number;
}

interface QueryHistoryItem {
  id: string;
  query: string;
  timestamp: string;
}

export function LeftSidebar() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [queryHistory, setQueryHistory] = useState<QueryHistoryItem[]>([]);
  const [status, setStatus] = useState<any>(null);

  const fetchData = async () => {
    try {
      const statsRes = await fetch('http://127.0.0.1:8000/api/status');
      const statsData = await statsRes.json();
      setStatus(statsData);

      const docsRes = await fetch('http://127.0.0.1:8000/api/documents');
      const docsData = await docsRes.json();
      setDocuments(docsData.files.map((name: string) => ({
        id: name,
        name: name,
        status: 'completed',
        pages: name.includes('CS302') ? 12 : name.includes('KTU') ? 24 : 8
      })));

      const histRes = await fetch('http://127.0.0.1:8000/api/history');
      const histData = await histRes.json();
      setQueryHistory(histData.history.map((q: string, i: number) => ({
        id: i.toString(),
        query: q,
        timestamp: 'Recently'
      })));
    } catch (e) {
      console.error("Sidebar fetch failed", e);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      for (const file of Array.from(files)) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('category', 'General');
        
        const tempId = Math.random().toString();
        setDocuments(prev => [{ id: tempId, name: file.name, status: 'uploading' }, ...prev]);

        try {
          await fetch('http://127.0.0.1:8000/api/upload', {
            method: 'POST',
            body: formData,
          });
          fetchData();
        } catch (e) {
          console.error("Upload failed", e);
          setDocuments(prev => prev.filter(d => d.id !== tempId));
        }
      }
    }
  };

  return (
    <div className="w-[260px] h-full bg-card border-r border-border flex flex-col">
      <div className="p-4 space-y-6 flex-1 overflow-y-auto">
        {/* Upload Documents Section */}
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3">Upload Documents</h3>
          <div className="border-2 border-dashed border-border rounded-xl p-4 hover:border-primary/50 transition-colors cursor-pointer group">
            <input
              type="file"
              multiple
              accept=".pdf,.docx,.csv,.pptx,.txt"
              onChange={handleFileUpload}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-2">
              <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center group-hover:bg-gray-100 transition-colors">
                <Upload className="w-5 h-5 text-black" />
              </div>
              <div className="text-center">
                <p className="text-xs text-foreground font-medium">Drop files here</p>
                <p className="text-xs text-muted-foreground">or click to browse</p>
              </div>
            </label>
          </div>
        </div>

        {/* Document List Section */}
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3">Documents ({documents.length})</h3>
          <div className="space-y-2">
            {documents.map((doc) => (
              <div key={doc.id} className="p-2.5 rounded-lg bg-muted/30 border border-border hover:bg-muted/50 transition-colors">
                <div className="flex items-start gap-2">
                  <FileText className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-foreground font-medium truncate">{doc.name}</p>
                    <div className="flex items-center gap-1.5 mt-1">
                      {doc.status === 'completed' && (
                        <>
                          <CheckCircle2 className="w-3 h-3 text-green-500" />
                          <span className="text-xs text-muted-foreground">{doc.pages} pages</span>
                        </>
                      )}
                      {doc.status === 'uploading' && (
                        <>
                          <Clock className="w-3 h-3 text-yellow-500 animate-spin" />
                          <span className="text-xs text-yellow-500">Uploading...</span>
                        </>
                      )}
                      {doc.status === 'processing' && (
                        <>
                          <Clock className="w-3 h-3 text-blue-500 animate-spin" />
                          <span className="text-xs text-blue-500">Processing...</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Knowledge Graph Status Section */}
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3">System Metrics</h3>
          <div className="p-3 rounded-lg bg-muted/30 border border-border">
            <div className="flex items-center gap-2 mb-3">
              <Network className="w-4 h-4 text-white" />
              <span className="text-xs font-semibold text-white">Engine: {status?.vector_ready ? 'Operational' : 'Initializing...'}</span>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted-foreground">Vector Chunks:</span>
                <span className="text-xs font-medium text-foreground">{status?.chunks || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted-foreground">Indexed PDFs:</span>
                <span className="text-xs font-medium text-foreground">{status?.pdfs || 0}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Query History Section */}
        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <History className="w-4 h-4" />
            Query History
          </h3>
          <div className="space-y-1.5">
            {queryHistory.map((item) => (
              <div 
                key={item.id} 
                className="p-2 rounded-lg hover:bg-muted/30 cursor-pointer transition-colors group"
              >
                <p className="text-xs text-foreground truncate group-hover:text-primary">{item.query}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{item.timestamp}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}