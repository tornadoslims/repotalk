import { create } from 'zustand';
import type { Conversation, Message, Reference } from '@/api/types';

interface ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  streamingContent: string;
  streamingReferences: Reference[];
  isStreaming: boolean;
  suggestedQuestions: string[];
  pinnedFiles: string[];
  totalCost: number;
  setConversations: (conversations: Conversation[]) => void;
  setCurrentConversation: (conversation: Conversation | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  appendStreamToken: (token: string) => void;
  addStreamReference: (ref: Reference) => void;
  setIsStreaming: (streaming: boolean) => void;
  setSuggestedQuestions: (questions: string[]) => void;
  clearStream: () => void;
  addPinnedFile: (file: string) => void;
  removePinnedFile: (file: string) => void;
  addCost: (cost: number) => void;
  finishStream: (cost?: number) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  currentConversation: null,
  messages: [],
  streamingContent: '',
  streamingReferences: [],
  isStreaming: false,
  suggestedQuestions: [],
  pinnedFiles: [],
  totalCost: 0,
  setConversations: (conversations) => set({ conversations }),
  setCurrentConversation: (conversation) => set({ currentConversation: conversation }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((s) => ({ messages: [...s.messages, message] })),
  appendStreamToken: (token) => set((s) => ({ streamingContent: s.streamingContent + token })),
  addStreamReference: (ref) => set((s) => ({ streamingReferences: [...s.streamingReferences, ref] })),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setSuggestedQuestions: (suggestedQuestions) => set({ suggestedQuestions }),
  clearStream: () => set({ streamingContent: '', streamingReferences: [], suggestedQuestions: [] }),
  addPinnedFile: (file) => set((s) => ({
    pinnedFiles: s.pinnedFiles.includes(file) ? s.pinnedFiles : [...s.pinnedFiles, file]
  })),
  removePinnedFile: (file) => set((s) => ({
    pinnedFiles: s.pinnedFiles.filter((f) => f !== file)
  })),
  addCost: (cost) => set((s) => ({ totalCost: s.totalCost + cost })),
  finishStream: (cost) => {
    const state = get();
    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      conversation_id: state.currentConversation?.id || '',
      role: 'assistant',
      content: state.streamingContent,
      references: state.streamingReferences,
      cost,
      created_at: new Date().toISOString(),
    };
    set((s) => ({
      messages: [...s.messages, assistantMessage],
      streamingContent: '',
      streamingReferences: [],
      isStreaming: false,
      totalCost: s.totalCost + (cost || 0),
    }));
  },
}));
