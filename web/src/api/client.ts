import type {
  Project,
  GraphData,
  GraphNode,
  TraceResult,
  ImpactResult,
  FileInfo,
  FileSource,
  DocNode,
  Conversation,
  Settings,
} from './types';

const API_BASE = '/api';

class ApiError extends Error {
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

export const api = {
  // Projects
  getProjects: () => request<Project[]>('/projects'),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (data: { name: string; path: string; description?: string }) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  updateProject: (id: string, data: Partial<Project>) =>
    request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteProject: (id: string) =>
    request<void>(`/projects/${id}`, { method: 'DELETE' }),

  // Graph
  getGraph: (projectId: string) => request<GraphData>(`/projects/${projectId}/graph`),
  getSubgraph: (projectId: string, nodeId: string, depth?: number) =>
    request<GraphData>(`/projects/${projectId}/graph/subgraph?node_id=${nodeId}${depth ? `&depth=${depth}` : ''}`),
  getGraphNodes: (projectId: string, query?: string) =>
    request<GraphNode[]>(`/projects/${projectId}/graph/nodes${query ? `?q=${encodeURIComponent(query)}` : ''}`),
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
  createConversation: (projectId: string) =>
    request<Conversation>(`/projects/${projectId}/conversations`, { method: 'POST', body: JSON.stringify({}) }),
  deleteConversation: (conversationId: string) =>
    request<void>(`/conversations/${conversationId}`, { method: 'DELETE' }),

  // Settings
  getSettings: () => request<Settings>('/settings'),
  updateSettings: (data: Partial<Settings>) =>
    request<Settings>('/settings', { method: 'PATCH', body: JSON.stringify(data) }),
};
