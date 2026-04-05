import React, { useEffect, useState } from 'react';
import { Save, FileText, Database, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';
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

export function KnowledgeGraphEditor({ onClose }: { onClose: () => void }) {
  const [files, setFiles] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState('');
  const [loadedContent, setLoadedContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [pendingDeletionWarning, setPendingDeletionWarning] = useState<null | { removed_count: number; removed_preview: string[] }>(null);

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
    } catch (error) {
      toast.error('Failed to load knowledge graph files');
    }
  };

  const loadFileContent = async (filename: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/kg-source/${filename}`);
      const data = await res.json();
      if (data.content !== undefined) {
        setFileContent(data.content);
        setLoadedContent(data.content);
      } else {
        toast.error('Failed to load file content');
      }
    } catch (error) {
      toast.error('Error connecting to backend');
    }
  };

  const restartKg = async () => {
    const res = await fetch('http://127.0.0.1:8000/api/kg-restart', {
      method: 'POST',
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.error || 'Knowledge graph restart failed');
    }
  };

  const saveFile = async (confirmDeletions = false) => {
    if (!selectedFile) {
      return false;
    }

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/kg-save/${selectedFile}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: fileContent, confirm_deletions: confirmDeletions }),
      });

      if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || error.error || `Failed to save ${selectedFile}`);
      }

      const data = await res.json();
      if (data.requires_confirmation) {
        setPendingDeletionWarning({
          removed_count: data.removed_count,
          removed_preview: data.removed_preview || [],
        });
        return false;
      }

      await restartKg();
      setLoadedContent(fileContent);
      setPendingDeletionWarning(null);
      toast.success(`Validated, saved, and refreshed ${selectedFile}`);
      return true;
    } catch (error) {
      toast.error((error as Error).message || 'Error saving file');
      return false;
    }
  };

  const handleSave = async () => {
    if (!selectedFile) {
      return;
    }

    setIsSaving(true);
    await saveFile(false);
    setIsSaving(false);
  };

  const hasUnsavedChanges = fileContent !== loadedContent;

  return (
    <div className="absolute inset-0 z-50 flex flex-col bg-background pt-16">
      <div className="flex items-center justify-between border-b border-border bg-card px-6 py-4">
        <div className="flex items-center gap-3">
          <Database className="h-5 w-5 text-primary" />
          <h2 className="text-xl font-semibold text-foreground">Knowledge Graph Editor</h2>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="flex items-center gap-2 rounded-lg bg-muted px-4 py-2 text-foreground transition-colors hover:bg-muted/80"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Chat
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="flex w-64 flex-col border-r border-border bg-muted/20">
          <div className="border-b border-border p-4">
            <h3 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
              Source Files (.ttl)
            </h3>
          </div>
          <div className="flex-1 space-y-1 overflow-y-auto p-2">
            {files.map((fileName) => (
              <button
                key={fileName}
                onClick={() => setSelectedFile(fileName)}
                className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                  selectedFile === fileName
                    ? 'bg-primary/10 font-medium text-primary'
                    : 'text-foreground hover:bg-muted'
                }`}
              >
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  <span className="truncate">{fileName}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-1 flex-col bg-[#1e1e1e]">
          <div className="flex items-center justify-between border-b border-border/10 bg-black/40 px-4 py-2">
            <div className="flex flex-col">
              <span className="text-xs font-mono text-gray-400">{selectedFile || 'Select a file'}</span>
              <span className="text-[11px] text-gray-500">
                {hasUnsavedChanges ? 'Unsaved changes' : 'Validated Turtle source'}
              </span>
            </div>
            <button
              onClick={handleSave}
              disabled={isSaving || !selectedFile}
              className="flex items-center gap-1.5 rounded bg-primary/20 px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/30 disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5" />
              {isSaving ? 'Saving...' : 'Validate & Save'}
            </button>
          </div>
          <div className="flex-1 p-4">
            <textarea
              value={fileContent}
              onChange={(e) => setFileContent(e.target.value)}
              spellCheck={false}
              className="h-full w-full resize-none bg-transparent font-mono text-sm text-[#d4d4d4] placeholder-gray-600 focus:outline-none"
              placeholder="Select a file to start editing..."
            />
          </div>
        </div>
      </div>

      <AlertDialog open={pendingDeletionWarning !== null}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Deletion warning</AlertDialogTitle>
            <AlertDialogDescription>
              This edit removes {pendingDeletionWarning?.removed_count || 0} existing knowledge graph triples. Please confirm before saving.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="max-h-40 overflow-y-auto rounded-lg border border-border bg-muted/30 p-3">
            <div className="space-y-2 text-xs text-foreground">
              {(pendingDeletionWarning?.removed_preview || []).map((item, index) => (
                <p key={index} className="break-all font-mono">
                  {item}
                </p>
              ))}
            </div>
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setPendingDeletionWarning(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={async () => {
                setIsSaving(true);
                await saveFile(true);
                setIsSaving(false);
              }}
            >
              Save Anyway
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
