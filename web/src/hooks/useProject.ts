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
    } catch {
      // Demo mode - use sample projects
      const sampleProjects: Project[] = [
        {
          id: 'demo-1',
          name: 'repotalk-backend',
          path: '/home/user/repotalk',
          description: 'FastAPI backend for RepoTalk',
          language: 'Python',
          file_count: 42,
          graph_node_count: 187,
          last_updated: new Date().toISOString(),
          status: 'ready',
          created_at: new Date().toISOString(),
        },
        {
          id: 'demo-2',
          name: 'web-frontend',
          path: '/home/user/repotalk/web',
          description: 'React frontend for RepoTalk',
          language: 'TypeScript',
          file_count: 28,
          graph_node_count: 93,
          last_updated: new Date().toISOString(),
          status: 'analyzing',
          created_at: new Date().toISOString(),
        },
      ];
      setProjects(sampleProjects);
      setError(null);
    } finally {
      setLoading(false);
    }
  }, [setProjects, setLoading, setError]);

  const loadFiles = useCallback(
    async (projectId: string) => {
      try {
        const files = await api.getFiles(projectId);
        setFiles(files);
      } catch {
        // Demo mode
        setFiles([
          { id: '1', path: 'auth.py', language: 'python', line_count: 48, size: 1420, last_modified: new Date().toISOString() },
          { id: '2', path: 'models.py', language: 'python', line_count: 36, size: 980, last_modified: new Date().toISOString() },
          { id: '3', path: 'main.py', language: 'python', line_count: 25, size: 650, last_modified: new Date().toISOString() },
          { id: '4', path: 'routes.py', language: 'python', line_count: 62, size: 1890, last_modified: new Date().toISOString() },
          { id: '5', path: 'database.py', language: 'python', line_count: 30, size: 820, last_modified: new Date().toISOString() },
          { id: '6', path: 'middleware.py', language: 'python', line_count: 44, size: 1200, last_modified: new Date().toISOString() },
        ]);
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
      } catch {
        return null;
      }
    },
    [setProjects]
  );

  return { loadProjects, loadFiles, createProject, setCurrentProject };
}
