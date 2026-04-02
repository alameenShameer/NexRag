import React, { useState, useEffect } from 'react';
import { Save, RefreshCw, FileText, Database } from 'lucide-react';
import { toast } from 'sonner';

export function KnowledgeGraphEditor({ onClose }: { onClose: () => void }) {
  const [files, setFiles] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);
  const [isRestarting, setIsRestarting] = useState(false);

  useEffect(() => {
    fetchFiles();
  }, []);

  useEffect(() => {
    if (selectedFile) {
      loadFileContent(selectedFile);
    }
  }, [selectedFile]);

  const fetchFiles = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/kg-files');
      const data = await res.json();
      if (data.files) {
        setFiles(data.files);
        if (data.files.length > 0 && !selectedFile) {
          setSelectedFile(data.files[0]);
        }
      }
    } catch (e) {
      toast.error('Failed to load files');
    }
  };

  const loadFileContent = async (filename: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/kg-source/${filename}`);
      const data = await res.json();
      if (data.content !== undefined) {
        setFileContent(data.content);
      } else {
        toast.error('Failed to load content');
      }
    } catch (e) {
      toast.error('Error connecting to backend');
    }
  };

  const handleSave = async () => {
    if (!selectedFile) return;
    setIsSaving(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/kg-source/${selectedFile}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: fileContent }),
      });
      if (res.ok) {
        toast.success(`Saved ${selectedFile}`);
      } else {
        toast.error(`Failed to save ${selectedFile}`);
      }
    } catch (e) {
      toast.error('Error saving file');
    } finally {
      setIsSaving(false);
    }
  };

  const handleRestart = async () => {
    setIsRestarting(true);
    toast.info('Merging graphs and restarting Fuseki...');
    try {
      const res = await fetch('http://127.0.0.1:8000/api/kg-restart', {
        method: 'POST',
      });
      if (res.ok) {
        toast.success('Knowledge Graph restarted successfully!');
      } else {
        const error = await res.json();
        toast.error(`Restart failed: ${error.error}`);
      }
    } catch (e) {
      toast.error('Error triggering restart');
    } finally {
      setIsRestarting(false);
    }
  };

  return (
    <div className="absolute inset-0 z-50 bg-background flex flex-col pt-16">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-card">
        <div className="flex items-center gap-3">
          <Database className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-semibold text-foreground">Knowledge Graph Editor</h2>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRestart}
            disabled={isRestarting}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500/10 text-orange-500 hover:bg-orange-500/20 font-medium transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isRestarting ? 'animate-spin' : ''}`} />
            Save &amp; Restart KG
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-muted text-foreground hover:bg-muted/80 transition-colors"
          >
            Close
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-64 border-r border-border bg-muted/20 flex flex-col">
          <div className="p-4 border-b border-border">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
              Source Files (.ttl)
            </h3>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {files.map(f => (
              <button
                key={f}
                onClick={() => setSelectedFile(f)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-colors ${
                  selectedFile === f
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-foreground hover:bg-muted'
                }`}
              >
                <FileText className="w-4 h-4" />
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Editor Area */}
        <div className="flex-1 flex flex-col bg-[#1e1e1e]">
          <div className="flex items-center justify-between px-4 py-2 bg-black/40 border-b border-border/10">
            <span className="text-xs font-mono text-gray-400">
              {selectedFile || 'Select a file'}
            </span>
            <button
              onClick={handleSave}
              disabled={isSaving || !selectedFile}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary/20 text-primary hover:bg-primary/30 text-xs font-medium transition-colors disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              {isSaving ? 'Saving...' : 'Save File'}
            </button>
          </div>
          <div className="flex-1 p-4">
            <textarea
              value={fileContent}
              onChange={(e) => setFileContent(e.target.value)}
              spellCheck={false}
              className="w-full h-full bg-transparent text-[#d4d4d4] font-mono text-sm resize-none focus:outline-none placeholder-gray-600"
              placeholder="Select a file to start editing..."
            />
          </div>
        </div>
      </div>
    </div>
  );
}
