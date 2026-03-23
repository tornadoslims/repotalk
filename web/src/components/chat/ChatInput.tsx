import { useState, useRef, useCallback } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { useProjectStore } from '@/stores/projectStore';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Send, Plus, X, Slash, AtSign } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend?: (message: string) => void;
}

export function ChatInput({ onSend }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [showSlash, setShowSlash] = useState(false);
  const [showAt, setShowAt] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { pinnedFiles, removePinnedFile, addPinnedFile, isStreaming } = useChatStore();
  const { files } = useProjectStore();

  const slashCommands = [
    { cmd: '/trace', desc: 'Trace code execution path' },
    { cmd: '/impact', desc: 'Analyze impact of changes' },
    { cmd: '/scope', desc: 'Set analysis scope' },
    { cmd: '/depth', desc: 'Set analysis depth' },
  ];

  const handleSubmit = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    onSend?.(trimmed);
    setInput('');
    setShowSlash(false);
    setShowAt(false);
  }, [input, isStreaming, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInput(val);
    // Check last word for slash/at triggers
    const lastWord = val.split(/\s/).pop() || '';
    setShowSlash(lastWord === '/');
    setShowAt(lastWord.startsWith('@') && lastWord.length >= 1);
  };

  const filteredFiles = files.filter((f) => {
    const search = input.split(/\s/).pop()?.slice(1) || '';
    return f.relative_path.toLowerCase().includes(search.toLowerCase());
  }).slice(0, 8);

  return (
    <div className="border-t border-border p-3 space-y-2">
      {/* Pinned files */}
      {pinnedFiles.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {pinnedFiles.map((file) => (
            <Badge key={file} variant="secondary" className="gap-1 text-xs">
              {file.split('/').pop()}
              <button onClick={() => removePinnedFile(file)} className="hover:text-destructive">
                <X className="w-3 h-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* Slash command dropdown */}
      {showSlash && (
        <div className="border border-border rounded-lg bg-popover p-1 space-y-0.5">
          {slashCommands.map((cmd) => (
            <button
              key={cmd.cmd}
              className="w-full text-left px-3 py-1.5 rounded text-sm hover:bg-muted transition-colors flex items-center gap-2"
              onClick={() => {
                setInput(input.replace(/\/\s*$/, cmd.cmd + ' '));
                setShowSlash(false);
                textareaRef.current?.focus();
              }}
            >
              <Slash className="w-3 h-3 text-primary" />
              <span className="font-mono text-primary">{cmd.cmd}</span>
              <span className="text-muted-foreground">{cmd.desc}</span>
            </button>
          ))}
        </div>
      )}

      {/* @ autocomplete dropdown */}
      {showAt && filteredFiles.length > 0 && (
        <div className="border border-border rounded-lg bg-popover p-1 space-y-0.5 max-h-48 overflow-y-auto">
          {filteredFiles.map((f) => (
            <button
              key={f.id}
              className="w-full text-left px-3 py-1.5 rounded text-sm hover:bg-muted transition-colors font-mono"
              onClick={() => {
                const words = input.split(/\s/);
                words[words.length - 1] = f.relative_path;
                setInput(words.join(' ') + ' ');
                setShowAt(false);
                textareaRef.current?.focus();
              }}
            >
              {f.relative_path}
            </button>
          ))}
        </div>
      )}

      {/* Input area */}
      <div className="flex items-end gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 shrink-0"
          onClick={() => {
            // Open a file picker dialog - for now just add a sample
            const sampleFile = files[0]?.relative_path;
            if (sampleFile) addPinnedFile(sampleFile);
          }}
        >
          <Plus className="w-4 h-4" />
        </Button>

        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your codebase... (/ for commands, @ for files)"
            className="resize-none min-h-[40px] max-h-[160px] pr-12 text-sm"
            rows={1}
            disabled={isStreaming}
          />
        </div>

        <Button
          size="icon"
          className="h-9 w-9 shrink-0"
          disabled={!input.trim() || isStreaming}
          onClick={handleSubmit}
        >
          <Send className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
