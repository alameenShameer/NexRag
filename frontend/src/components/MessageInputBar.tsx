import { Send } from 'lucide-react';
import { useState } from 'react';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  ready?: boolean;
  uploadsInProgress?: number;
}

export function MessageInputBar({
  onSendMessage,
  disabled = false,
  ready = true,
  uploadsInProgress = 0,
}: MessageInputProps) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (disabled || !ready) {
      return;
    }
    if (input.trim()) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="border-t border-border bg-card px-6 py-4">
      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
        <div className="relative flex items-center gap-2 bg-muted/30 border border-border rounded-full px-4 py-2.5 focus-within:border-primary/50 transition-colors">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={ready ? 'Ask about MESITAM, departments, facilities, regulations, placements, or events...' : 'Initializing backend / Indexing documents...'}
            rows={1}
            disabled={disabled || !ready}
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none resize-none py-1"
            style={{ maxHeight: '120px' }}
          />

          <button
            type="submit"
            disabled={disabled || !ready || !input.trim()}
            className="flex-shrink-0 w-8 h-8 rounded-lg bg-primary hover:bg-primary/90 disabled:bg-muted disabled:cursor-not-allowed flex items-center justify-center transition-colors"
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
        <p className="mt-2 px-2 text-xs text-muted-foreground">
          {!ready
            ? 'The chatbot will answer only after the MESITAM knowledge base finishes loading.'
            : disabled
              ? 'NexRag is preparing a response...'
              : uploadsInProgress > 0
                ? 'A recently uploaded document is still indexing and may not be searchable yet.'
                : 'Press Enter to send. Shift+Enter adds a new line.'}
        </p>
      </form>
    </div>
  );
}
