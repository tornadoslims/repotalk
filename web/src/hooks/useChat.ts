import { useCallback } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { useSSE } from './useSSE';
import { api } from '@/api/client';
import { useGraphStore } from '@/stores/graphStore';
import type { Message } from '@/api/types';

export function useChat() {
  const {
    currentConversation,
    setCurrentConversation,
    setConversations,
    addMessage,
    appendStreamToken,
    addStreamReference,
    setIsStreaming,
    setSuggestedQuestions,
    clearStream,
    finishStream,
    pinnedFiles,
  } = useChatStore();
  const { setHighlightedNodes } = useGraphStore();
  const { send, abort } = useSSE();

  const sendMessage = useCallback(
    async (content: string) => {
      let convId = currentConversation?.id;

      // Create conversation if none exists
      if (!convId) {
        try {
          const projectId = 'default'; // Would come from project store in real app
          const conv = await api.createConversation(projectId);
          setCurrentConversation(conv);
          convId = conv.id;
        } catch {
          // Fallback for demo mode
          convId = crypto.randomUUID();
          setCurrentConversation({
            id: convId,
            project_id: 'default',
            title: content.slice(0, 50),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            message_count: 0,
          });
        }
      }

      // Add user message
      const userMsg: Message = {
        id: crypto.randomUUID(),
        conversation_id: convId,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      };
      addMessage(userMsg);
      clearStream();
      setIsStreaming(true);

      send(convId, content, {
        onToken: (token) => appendStreamToken(token),
        onReference: (file, line) => addStreamReference({ file, line }),
        onGraphHighlight: (nodes) => setHighlightedNodes(nodes),
        onSuggestions: (questions) => setSuggestedQuestions(questions),
        onDone: (cost) => finishStream(cost),
        onError: (message) => {
          // On error, show it as a message and stop streaming
          finishStream(0);
          console.error('Chat error:', message);
        },
      }, { pinned_files: pinnedFiles });
    },
    [currentConversation, pinnedFiles, send, addMessage, appendStreamToken, addStreamReference, clearStream, setIsStreaming, setSuggestedQuestions, finishStream, setHighlightedNodes, setCurrentConversation]
  );

  const loadConversations = useCallback(
    async (projectId: string) => {
      try {
        const convs = await api.getConversations(projectId);
        setConversations(convs);
      } catch {
        // Demo mode - use empty list
        setConversations([]);
      }
    },
    [setConversations]
  );

  return { sendMessage, abort, loadConversations };
}
