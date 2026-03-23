import { useCallback } from 'react';
import { useProjectStore } from '@/stores/projectStore';
import { api } from '@/api/client';
import type { Project } from '@/api/types';

export function useProject() {
  const { setProjects, setCurrentProject, setFiles, setLoading, setError } = useProjectStore();

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const projects = await api.getProjects();
      setProjects(projects);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load projects';
      console.error('Failed to load projects:', message);
      setError(message);
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, [setProjects, setLoading, setError]);

  const loadFiles = useCallback(
    async (projectId: string) => {
      try {
        const files = await api.getFiles(projectId);
        setFiles(files);
      } catch (err) {
        console.error('Failed to load files:', err);
        setFiles([]);
      }
    },
    [setFiles]
  );

  const createProject = useCallback(
    async (data: { name: string; path: string; description?: string }) => {
      try {
        const project = await api.createProject(data);
        setProjects([...useProjectStore.getState().projects, project]);
        return project;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create project';
        console.error('Failed to create project:', message);
        setError(message);
        return null;
      }
    },
    [setProjects, setError]
  );

  const indexProject = useCallback(
    async (projectId: string) => {
      try {
        const status = await api.indexProject(projectId);
        return status;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to start indexing';
        console.error('Failed to index project:', message);
        setError(message);
        return null;
      }
    },
    [setError]
  );

  return { loadProjects, loadFiles, createProject, indexProject, setCurrentProject };
}
