import { useCallback } from 'react';
import { useGraphStore } from '@/stores/graphStore';
import { api } from '@/api/client';

export function useGraph() {
  const { setGraphData, setSelectedNode } = useGraphStore();

  const loadGraph = useCallback(
    async (projectId: string) => {
      try {
        const data = await api.getGraph(projectId);
        setGraphData(data);
      } catch {
        // Will use sample data via graphStore
        setGraphData(null);
      }
    },
    [setGraphData]
  );

  const traceNode = useCallback(
    async (projectId: string, nodeId: string) => {
      try {
        const result = await api.traceNode(projectId, nodeId);
        return result;
      } catch {
        return null;
      }
    },
    []
  );

  const impactNode = useCallback(
    async (projectId: string, nodeId: string) => {
      try {
        const result = await api.impactNode(projectId, nodeId);
        return result;
      } catch {
        return null;
      }
    },
    []
  );

  return { loadGraph, traceNode, impactNode };
}
