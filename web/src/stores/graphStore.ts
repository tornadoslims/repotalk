import { create } from 'zustand';
import type { GraphData, GraphNode } from '@/api/types';

interface GraphState {
  graphData: GraphData | null;
  selectedNode: GraphNode | null;
  highlightedNodes: string[];
  edgeFilters: Record<string, boolean>;
  layoutMode: 'fcose' | 'circle' | 'grid' | 'breadthfirst';
  searchQuery: string;
  setGraphData: (data: GraphData | null) => void;
  setSelectedNode: (node: GraphNode | null) => void;
  setHighlightedNodes: (nodes: string[]) => void;
  toggleEdgeFilter: (edgeType: string) => void;
  setLayoutMode: (mode: 'fcose' | 'circle' | 'grid' | 'breadthfirst') => void;
  setSearchQuery: (query: string) => void;
}

export const useGraphStore = create<GraphState>((set) => ({
  graphData: null,
  selectedNode: null,
  highlightedNodes: [],
  edgeFilters: {
    imports: true,
    calls: true,
    inherits: true,
    composes: true,
    decorates: true,
    defines: true,
    contains: true,
  },
  layoutMode: 'fcose',
  searchQuery: '',
  setGraphData: (graphData) => set({ graphData }),
  setSelectedNode: (selectedNode) => set({ selectedNode }),
  setHighlightedNodes: (highlightedNodes) => set({ highlightedNodes }),
  toggleEdgeFilter: (edgeType) =>
    set((s) => ({
      edgeFilters: { ...s.edgeFilters, [edgeType]: !s.edgeFilters[edgeType] },
    })),
  setLayoutMode: (layoutMode) => set({ layoutMode }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
}));
