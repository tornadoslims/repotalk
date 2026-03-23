import { create } from 'zustand';
import type { Project, FileInfo } from '@/api/types';

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  files: FileInfo[];
  loading: boolean;
  error: string | null;
  setProjects: (projects: Project[]) => void;
  setCurrentProject: (project: Project | null) => void;
  setFiles: (files: FileInfo[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  currentProject: null,
  files: [],
  loading: false,
  error: null,
  setProjects: (projects) => set({ projects }),
  setCurrentProject: (currentProject) => set({ currentProject }),
  setFiles: (files) => set({ files }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
