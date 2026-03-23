import type { Reference } from '@/api/types';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { Bot } from 'lucide-react';

interface StreamingMessageProps {
  content: string;
  references: Reference[];
}

export function StreamingMessage({ content, references }: StreamingMessageProps) {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
        <Bot className="w-4 h-4 text-primary animate-pulse" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="rounded-lg px-4 py-3 bg-card border border-border">
          {content ? (
            <div className="streaming-cursor">
              <MarkdownRenderer content={content} />
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              Thinking...
            </div>
          )}
        </div>
        {references.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {references.map((ref, i) => (
              <span key={i} className="text-xs px-2 py-1 rounded bg-muted text-muted-foreground font-mono">
                {ref.file}{ref.line ? `:${ref.line}` : ''}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
