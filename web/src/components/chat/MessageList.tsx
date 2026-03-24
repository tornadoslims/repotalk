import { useEffect, useRef } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatMessage } from './ChatMessage';
import { StreamingMessage } from './StreamingMessage';
import { Bot } from 'lucide-react';

interface MessageListProps {
  onSend?: (message: string) => void;
}

export function MessageList({ onSend }: MessageListProps) {
  const { messages, isStreaming, streamingContent, streamingReferences } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4 max-w-md">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto">
            <Bot className="w-8 h-8 text-primary" />
          </div>
          <h3 className="text-lg font-medium">Ask anything about your codebase</h3>
          <p className="text-sm text-muted-foreground">
            I can trace code paths, explain architecture, find dependencies, and help you understand complex code.
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {['How does auth work?', 'Trace the login flow', 'What calls this function?', 'Show me the API layer'].map((q) => (
              <button
                key={q}
                onClick={() => onSend?.(q)}
                className="px-3 py-2 rounded-lg border border-border hover:bg-muted transition-colors text-left text-muted-foreground hover:text-foreground"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1">
      <div className="p-4 space-y-4 max-w-3xl mx-auto">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {isStreaming && (
          <StreamingMessage content={streamingContent} references={streamingReferences} />
        )}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
