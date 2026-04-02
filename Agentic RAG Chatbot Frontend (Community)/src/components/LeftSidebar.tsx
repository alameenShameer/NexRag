import { Upload, FileText, CheckCircle2, Clock, Network, History } from 'lucide-react';
import { useState } from 'react';

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
  const [documents, setDocuments] = useState<Document[]>([
    { id: '1', name: 'Syllabus_CS302.pdf', status: 'completed', pages: 12 },
    { id: '2', name: 'Faculty_Database.pdf', status: 'completed', pages: 8 },
    { id: '3', name: 'KTU_Guidelines.pdf', status: 'completed', pages: 24 },
  ]);

  const [queryHistory, setQueryHistory] = useState<QueryHistoryItem[]>([
    { id: '1', query: 'Who teaches Operating Systems?', timestamp: '2m ago' },
    { id: '2', query: 'Explain Module 3 syllabus', timestamp: '15m ago' },
    { id: '3', query: 'What are KTU exam rules?', timestamp: '1h ago' },
  ]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      Array.from(files).forEach((file) => {
        const newDoc: Document = {
          id: Date.now().toString() + Math.random(),
          name: file.name,
          status: 'uploading',
        };
        setDocuments(prev => [newDoc, ...prev]);
        
        // Simulate upload progress
        setTimeout(() => {
          setDocuments(prev => prev.map(doc => 
            doc.id === newDoc.id ? { ...doc, status: 'processing' } : doc
          ));
        }, 1500);
        
        setTimeout(() => {
          setDocuments(prev => prev.map(doc => 
            doc.id === newDoc.id ? { ...doc, status: 'completed', pages: Math.floor(Math.random() * 20) + 5 } : doc
          ));
        }, 3500);
      });
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
          <h3 className="text-sm font-semibold text-foreground mb-3">Knowledge Graph</h3>
          <div className="p-3 rounded-lg bg-muted/30 border border-border">
            <div className="flex items-center gap-2 mb-3">
              <Network className="w-4 h-4 text-white" />
              <span className="text-xs font-semibold text-white">Status: Loaded</span>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted-foreground">Nodes:</span>
                <span className="text-xs font-medium text-foreground">1,247</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted-foreground">Edges:</span>
                <span className="text-xs font-medium text-foreground">3,891</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted-foreground">Entities:</span>
                <span className="text-xs font-medium text-foreground">Faculty, Courses, Rules</span>
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