import type {
  Project,
  GraphDataRaw,
  GraphNode,
  TraceResult,
  ImpactResult,
  FileInfo,
  FileSource,
  DocNode,
  Conversation,
  Settings,
  IndexStatus,
} from './types';
import { transformGraphData, deriveProjectStatus } from './types';
import type { GraphData } from './types';

const API_BASE = '/api';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json();
}

// Transform raw project from backend (no status field) to frontend Project
function toProject(raw: Record<string, unknown>): Project {
  const p = raw as Omit<Project, 'status'> & { status?: string };
  return {
    ...p,
    status: (p.status as Project['status']) || deriveProjectStatus(p as Omit<Project, 'status'>),
  } as Project;
}

export const api = {
  // Projects
  getProjects: async (): Promise<Project[]> => {
    const raw = await request<Record<string, unknown>[]>('/projects');
    return raw.map(toProject);
  },
  getProject: async (id: string): Promise<Project> => {
    const raw = await request<Record<string, unknown>>(`/projects/${id}`);
    return toProject(raw);
  },
  createProject: async (data: { name: string; path: string; description?: string }): Promise<Project> => {
    const raw = await request<Record<string, unknown>>('/projects', {
      method: 'POST',
      body: JSON.stringify({ name: data.name, source_path: data.path }),
    });
    return toProject(raw);
  },
  updateProject: (id: string, data: Partial<Project>) =>
    request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteProject: (id: string) =>
    request<void>(`/projects/${id}`, { method: 'DELETE' }),

  // Indexing
  indexProject: (id: string) =>
    request<IndexStatus>(`/projects/${id}/index`, { method: 'POST' }),
  getIndexStatus: (id: string) =>
    request<IndexStatus>(`/projects/${id}/index-status`),

  // Graph - transform raw backend data to frontend format
  getGraph: async (projectId: string): Promise<GraphData> => {
    const raw = await request<GraphDataRaw>(`/projects/${projectId}/graph`);
    return transformGraphData(raw);
  },
  getSubgraph: async (projectId: string, nodeId: string, depth?: number): Promise<GraphData> => {
    const raw = await request<GraphDataRaw>(
      `/projects/${projectId}/graph/subgraph?node=${nodeId}${depth ? `&depth=${depth}` : ''}`
    );
    return transformGraphData(raw);
  },
  getGraphNodes: (projectId: string, query?: string) =>
    request<GraphNode[]>(`/projects/${projectId}/graph/nodes${query ? `?search=${encodeURIComponent(query)}` : ''}`),
  traceNode: (projectId: string, nodeId: string) =>
    request<TraceResult>(`/projects/${projectId}/graph/trace/${nodeId}`),
  impactNode: (projectId: string, nodeId: string) =>
    request<ImpactResult>(`/projects/${projectId}/graph/impact/${nodeId}`),

  // Files
  getFiles: (projectId: string) => request<FileInfo[]>(`/projects/${projectId}/files`),
  getFileSource: (projectId: string, fileId: string) =>
    request<FileSource>(`/projects/${projectId}/files/${fileId}/source`),
  getFileDoc: (projectId: string, fileId: string) =>
    request<DocNode>(`/projects/${projectId}/files/${fileId}/doc`),

  // Docs
  getDocsTree: (projectId: string) => request<DocNode[]>(`/projects/${projectId}/docs/tree`),
  searchDocs: (projectId: string, query: string) =>
    request<DocNode[]>(`/projects/${projectId}/docs/search?q=${encodeURIComponent(query)}`),

  // Conversations
  getConversations: (projectId: string) =>
    request<Conversation[]>(`/projects/${projectId}/conversations`),
  createConversation: (projectId: string, title?: string) =>
    request<Conversation>(`/projects/${projectId}/conversations`, {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),
  deleteConversation: (conversationId: string) =>
    request<void>(`/conversations/${conversationId}`, { method: 'DELETE' }),

  // Settings
  getSettings: () => request<Settings>('/settings'),
  updateSettings: (data: Partial<Settings>) =>
    request<Settings>('/settings', { method: 'PATCH', body: JSON.stringify(data) }),
};
