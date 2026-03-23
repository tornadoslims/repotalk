import { useState } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { useUIStore } from '@/stores/uiStore';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { SuggestedQuestions } from './SuggestedQuestions';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { PanelLeftClose, PanelLeft, Plus, MessageSquare, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ChatPanel() {
  const { conversations, currentConversation, setCurrentConversation, messages, suggestedQuestions } = useChatStore();
  const { conversationListOpen, setConversationListOpen } = useUIStore();

  return (
    <div className="flex h-full">
      {/* Conversation sidebar */}
      <div className={cn(
        'border-r border-border bg-card/50 flex flex-col transition-all duration-200',
        conversationListOpen ? 'w-64' : 'w-0 overflow-hidden'
      )}>
        <div className="p-3 border-b border-border flex items-center justify-between">
          <span className="text-sm font-medium">Conversations</span>
          <Button variant="ghost" size="icon" className="h-7 w-7">
            <Plus className="w-4 h-4" />
          </Button>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {conversations.length === 0 ? (
              <div className="text-xs text-muted-foreground p-3 text-center">No conversations yet</div>
            ) : (
              conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => setCurrentConversation(conv)}
                  className={cn(
                    'w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center justify-between group',
                    currentConversation?.id === conv.id
                      ? 'bg-primary/10 text-primary'
                      : 'hover:bg-muted text-foreground'
                  )}
                >
                  <div className="flex items-center gap-2 truncate">
                    <MessageSquare className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{conv.title || 'New Chat'}</span>
                  </div>
                  <Trash2 className="w-3 h-3 opacity-0 group-hover:opacity-50 hover:!opacity-100 shrink-0" />
                </button>
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat header */}
        <div className="h-10 border-b border-border flex items-center px-3 gap-2 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setConversationListOpen(!conversationListOpen)}
          >
            {conversationListOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeft className="w-4 h-4" />}
          </Button>
          <span className="text-sm font-medium truncate">
            {currentConversation?.title || 'New Conversation'}
          </span>
        </div>

        {/* Messages */}
        <MessageList />

        {/* Suggestions */}
        {suggestedQuestions.length > 0 && <SuggestedQuestions />}

        {/* Input */}
        <ChatInput />
      </div>
    </div>
  );
}
