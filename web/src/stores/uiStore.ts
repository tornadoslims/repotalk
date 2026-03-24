import { create } from 'zustand';

type Theme = 'dark' | 'light';

export interface SourceTab {
  id: string;
  filename: string;
  content: string;
  language: string;
  highlights?: Array<{ startLine: number; endLine: number }>;
}

interface UIState {
  theme: Theme;
  leftPaneWidth: number;
  activeContextTab: string;
  sidebarOpen: boolean;
  conversationListOpen: boolean;
  sourceTabs: SourceTab[];
  activeSourceTab: string;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  setLeftPaneWidth: (width: number) => void;
  setActiveContextTab: (tab: string) => void;
  setSidebarOpen: (open: boolean) => void;
  setConversationListOpen: (open: boolean) => void;
  addSourceTab: (tab: SourceTab) => void;
  removeSourceTab: (id: string) => void;
  setActiveSourceTab: (id: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  theme: 'dark',
  leftPaneWidth: 60,
  activeContextTab: 'source',
  sidebarOpen: false,
  conversationListOpen: false,
  sourceTabs: [],
  activeSourceTab: '',
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
  addSourceTab: (tab) =>
    set((s) => {
      const existing = s.sourceTabs.find((t) => t.id === tab.id);
      if (existing) {
        // Update content and activate
        return {
          sourceTabs: s.sourceTabs.map((t) => (t.id === tab.id ? tab : t)),
          activeSourceTab: tab.id,
        };
      }
      return {
        sourceTabs: [...s.sourceTabs, tab],
        activeSourceTab: tab.id,
      };
    }),
  removeSourceTab: (id) =>
    set((s) => {
      const newTabs = s.sourceTabs.filter((t) => t.id !== id);
      return {
        sourceTabs: newTabs,
        activeSourceTab: s.activeSourceTab === id ? (newTabs[0]?.id || '') : s.activeSourceTab,
      };
    }),
  setActiveSourceTab: (activeSourceTab) => set({ activeSourceTab }),
}));
