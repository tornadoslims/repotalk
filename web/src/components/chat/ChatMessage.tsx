import type { Message } from '@/api/types';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { ActionButtons } from './ActionButtons';
import { useUIStore } from '@/stores/uiStore';
import { useProjectStore } from '@/stores/projectStore';
import { api } from '@/api/client';
import { Bot, User } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const { setActiveContextTab, addSourceTab } = useUIStore();
  const isAssistant = message.role === 'assistant';

  const handleReferenceClick = async (file: string, line?: number) => {
    setActiveContextTab('source');

    const projectId = useProjectStore.getState().currentProject?.id;
    if (!projectId) return;

    // Try to find the file by matching relative_path
    const files = useProjectStore.getState().files;
    const match = files.find(
      (f) => f.relative_path === file || f.relative_path.endsWith(file) || file.endsWith(f.relative_path)
    );

    if (match) {
      try {
        const source = await api.getFileSource(projectId, match.id);
        addSourceTab({
          id: match.id,
          filename: match.relative_path.split('/').pop() || file,
          content: source.content,
          language: source.language || match.language || 'plaintext',
          highlights: line ? [{ startLine: line, endLine: line }] : undefined,
        });
      } catch (err) {
        console.error('Failed to load file source:', err);
      }
    }
  };

  return (
    <div className={cn('flex gap-3', !isAssistant && 'flex-row-reverse')}>
      <div className={cn(
        'w-8 h-8 rounded-lg flex items-center justify-center shrink-0',
        isAssistant ? 'bg-primary/10' : 'bg-secondary'
      )}>
        {isAssistant ? <Bot className="w-4 h-4 text-primary" /> : <User className="w-4 h-4 text-secondary-foreground" />}
      </div>
      <div className={cn('flex-1 min-w-0', !isAssistant && 'flex flex-col items-end')}>
        <div className={cn(
          'rounded-lg px-4 py-3',
          isAssistant ? 'bg-card border border-border' : 'bg-primary text-primary-foreground'
        )}>
          {isAssistant ? (
            <MarkdownRenderer content={message.content} onReferenceClick={handleReferenceClick} />
          ) : (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          )}
        </div>

        {/* References chips */}
        {isAssistant && message.references && message.references.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {message.references.map((ref, i) => (
              <button
                key={i}
                onClick={() => handleReferenceClick(ref.file, ref.line)}
                className="text-xs px-2 py-1 rounded bg-muted hover:bg-muted/80 text-muted-foreground font-mono transition-colors"
              >
                {ref.file}{ref.line ? `:${ref.line}` : ''}
              </button>
            ))}
          </div>
        )}

        {/* Action buttons for assistant messages */}
        {isAssistant && <ActionButtons messageId={message.id} />}

        {/* Cost */}
        {isAssistant && message.cost != null && (
          <span className="text-[10px] text-muted-foreground mt-1">${message.cost.toFixed(4)}</span>
        )}
      </div>
    </div>
  );
}
