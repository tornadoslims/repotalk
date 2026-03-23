import { create } from 'zustand';

type Theme = 'dark' | 'light';

interface UIState {
  theme: Theme;
  leftPaneWidth: number;
  activeContextTab: string;
  sidebarOpen: boolean;
  conversationListOpen: boolean;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  setLeftPaneWidth: (width: number) => void;
  setActiveContextTab: (tab: string) => void;
  setSidebarOpen: (open: boolean) => void;
  setConversationListOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  theme: 'dark',
  leftPaneWidth: 60,
  activeContextTab: 'source',
  sidebarOpen: false,
  conversationListOpen: false,
  setTheme: (theme) => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    set({ theme });
  },
  toggleTheme: () =>
    set((s) => {
      const next = s.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.classList.toggle('dark', next === 'dark');
      return { theme: next };
    }),
  setLeftPaneWidth: (leftPaneWidth) => set({ leftPaneWidth }),
  setActiveContextTab: (activeContextTab) => set({ activeContextTab }),
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setConversationListOpen: (conversationListOpen) => set({ conversationListOpen }),
}));
