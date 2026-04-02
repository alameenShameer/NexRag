import { Paperclip, Mic, Send } from 'lucide-react';
import { useState } from 'react';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
}

export function MessageInputBar({ onSendMessage }: MessageInputProps) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
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
          <button
            type="button"
            className="flex-shrink-0 w-8 h-8 rounded-lg hover:bg-muted flex items-center justify-center transition-colors"
          >
            <Paperclip className="w-4 h-4 text-muted-foreground" />
          </button>
          
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your college..."
            rows={1}
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none resize-none py-1"
            style={{ maxHeight: '120px' }}
          />
          
          <button
            type="button"
            className="flex-shrink-0 w-8 h-8 rounded-lg hover:bg-muted flex items-center justify-center transition-colors"
          >
            <Mic className="w-4 h-4 text-muted-foreground" />
          </button>
          
          <button
            type="submit"
            disabled={!input.trim()}
            className="flex-shrink-0 w-8 h-8 rounded-lg bg-primary hover:bg-primary/90 disabled:bg-muted disabled:cursor-not-allowed flex items-center justify-center transition-colors"
          >
            <Send className="w-4 h-4 text-white" />
          </button>
        </div>
      </form>
    </div>
  );
}
