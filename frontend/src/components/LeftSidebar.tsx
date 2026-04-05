import { Upload, FileText, CheckCircle2, Clock, History, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog';

interface Document {
  id: string;
  name: string;
  status: 'uploaded' | 'chunking' | 'embedding' | 'indexed' | 'failed';
  progress?: number;
  message?: string;
  error?: string | null;
}

interface QueryHistoryItem {
  id: string;
  question: string;
  answer: string;
  timestamp: string;
  intent?: string;
}

type SidebarTab = 'documents' | 'history';

export function LeftSidebar({ onOpenHistoryEntry }: { onOpenHistoryEntry?: (item: QueryHistoryItem) => void }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [queryHistory, setQueryHistory] = useState<QueryHistoryItem[]>([]);
  const [activeTab, setActiveTab] = useState<SidebarTab>('documents');
  const [pendingDeleteDoc, setPendingDeleteDoc] = useState<string | null>(null);
  const [deletingDoc, setDeletingDoc] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const docsRes = await fetch('http://127.0.0.1:8000/api/documents');
      const docsData = await docsRes.json();
      setDocuments((docsData.documents || []).map((doc: any) => ({
        id: doc.id || doc.name,
        name: doc.name,
        status: doc.status || 'indexed',
        progress: doc.progress || 0,
        message: doc.message,
        error: doc.error,
      })));
    } catch (error) {
      console.error('Documents fetch failed', error);
    }

    try {
      const histRes = await fetch('http://127.0.0.1:8000/api/history');
      const histData = await histRes.json();
      setQueryHistory(histData.history || []);
    } catch (error) {
      console.error('History fetch failed', error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = window.setInterval(fetchData, 5000);
    return () => window.clearInterval(interval);
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) {
      return;
    }

    for (const file of Array.from(files)) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('category', 'General');

      const tempId = Math.random().toString();
      setDocuments(prev => [{ id: tempId, name: file.name, status: 'uploaded', progress: 15, message: 'File uploaded' }, ...prev]);

      try {
        const res = await fetch('http://127.0.0.1:8000/api/upload', {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) {
          throw new Error('Upload failed');
        }

        fetchData();
      } catch (error) {
        console.error('Upload failed', error);
        setDocuments(prev => prev.filter(doc => doc.id !== tempId));
      }
    }

    e.target.value = '';
  };

  const confirmDeleteDocument = async () => {
    if (!pendingDeleteDoc) {
      return;
    }

    const docToDelete = pendingDeleteDoc;
    const previousDocuments = documents;
    setPendingDeleteDoc(null);
    setDeletingDoc(docToDelete);
    setDocuments(prev => prev.filter(doc => doc.name !== docToDelete));

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/documents/${encodeURIComponent(docToDelete)}`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        throw new Error('Delete failed');
      }

      fetchData();
    } catch (error) {
      console.error('Delete failed', error);
      setDocuments(previousDocuments);
    } finally {
      setDeletingDoc(null);
    }
  };

  const tabs = [
    { id: 'documents' as const, label: `Documents (${documents.length})`, icon: FileText },
    { id: 'history' as const, label: 'Query History', icon: History },
  ];

  return (
    <div className="w-[300px] h-full bg-card border-r border-border flex flex-col">
      <div className="p-4 border-b border-border">
        <h3 className="text-sm font-semibold text-foreground mb-3">Upload Documents</h3>
        <div className="border-2 border-dashed border-border rounded-xl p-4 hover:border-primary/50 transition-colors cursor-pointer group">
          <input
            type="file"
            multiple
            accept=".pdf"
            onChange={handleFileUpload}
            className="hidden"
            id="file-upload"
          />
          <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-2">
            <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center group-hover:bg-gray-100 transition-colors">
              <Upload className="w-5 h-5 text-black" />
            </div>
            <div className="text-center">
              <p className="text-xs text-foreground font-medium">Upload PDF files</p>
              <p className="text-xs text-muted-foreground">Click to browse</p>
            </div>
          </label>
        </div>
      </div>

      <div className="flex border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 px-3 py-3 text-xs font-medium transition-colors relative ${
              activeTab === tab.id ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <div className="flex items-center justify-center gap-1.5">
              <tab.icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </div>
            {activeTab === tab.id ? <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" /> : null}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'documents' ? (
          <div className="space-y-2">
            {documents.length === 0 ? (
              <div className="rounded-lg border border-border bg-muted/20 p-4 text-xs leading-relaxed text-muted-foreground">
                No PDFs are indexed yet. Upload a document above to add it to the knowledge base.
              </div>
            ) : null}

            {documents.map((doc) => (
              <div key={doc.id} className="rounded-lg border border-border bg-muted/30 p-3 transition-colors hover:bg-muted/50">
                <div className="flex items-start gap-2">
                  <FileText className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium text-foreground">{doc.name}</p>
                    <div className="mt-1 flex items-center gap-1.5">
                      {doc.status === 'indexed' ? (
                        <>
                          <CheckCircle2 className="h-3 w-3 text-green-500" />
                          <span className="text-xs text-muted-foreground">{doc.message || 'Indexed and searchable'}</span>
                        </>
                      ) : doc.status === 'failed' ? (
                        <>
                          <Clock className="h-3 w-3 text-rose-500" />
                          <span className="text-xs text-rose-400">{doc.error || doc.message || 'Indexing failed'}</span>
                        </>
                      ) : (
                        <>
                          <Clock className="h-3 w-3 animate-spin text-yellow-500" />
                          <span className="text-xs text-yellow-500">{doc.message || 'Uploading and indexing...'}</span>
                        </>
                      )}
                    </div>
                    {doc.status !== 'indexed' ? (
                      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${doc.progress || 0}%` }} />
                      </div>
                    ) : null}
                  </div>
                  {doc.status === 'indexed' || doc.status === 'failed' ? (
                    <button
                      type="button"
                      onClick={() => setPendingDeleteDoc(doc.name)}
                      disabled={deletingDoc === doc.name}
                      className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-rose-500/10 hover:text-rose-400"
                      title={`Remove ${doc.name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {queryHistory.length === 0 ? (
              <div className="rounded-lg border border-border bg-muted/20 p-4 text-xs leading-relaxed text-muted-foreground">
                No previous conversations yet. Your recent prompts will appear here automatically.
              </div>
            ) : null}

            {queryHistory.map((item) => (
              <button
                type="button"
                key={item.id}
                onClick={() => onOpenHistoryEntry?.(item)}
                className="w-full rounded-lg border border-border bg-muted/20 p-3 text-left transition-colors hover:border-primary/40 hover:bg-muted/40"
              >
                <p className="line-clamp-2 text-xs font-medium text-foreground">{item.question}</p>
                <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                  {item.answer || 'Earlier answer'}
                </p>
                <p className="mt-2 text-[11px] text-muted-foreground/80">
                  {item.timestamp || item.intent || 'Saved conversation'}
                </p>
              </button>
            ))}
          </div>
        )}
      </div>

      <AlertDialog open={pendingDeleteDoc !== null} onOpenChange={(open) => !open && setPendingDeleteDoc(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove document from NexRag?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDeleteDoc
                ? `This will remove "${pendingDeleteDoc}" from the local document library and rebuild the searchable vector index. Existing chat history will stay, but future answers will no longer use this PDF.`
                : 'This will remove the selected PDF from the indexed document library.'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setPendingDeleteDoc(null)}>Keep document</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDeleteDocument}>Remove document</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
