import { useCallback } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { useProjectStore } from '@/stores/projectStore';
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
      const projectId = useProjectStore.getState().currentProject?.id;
      if (!projectId) {
        console.error('No project selected');
        return;
      }

      let convId = currentConversation?.id;

      // Create conversation if none exists
      if (!convId) {
        try {
          const conv = await api.createConversation(projectId, content.slice(0, 50));
          setCurrentConversation(conv);
          convId = conv.id;
        } catch (err) {
          console.error('Failed to create conversation:', err);
          return;
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
        setConversations([]);
      }
    },
    [setConversations]
  );

  return { sendMessage, abort, loadConversations };
}
