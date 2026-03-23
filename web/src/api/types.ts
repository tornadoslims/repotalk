export interface Project {
  id: string;
  name: string;
  source_path: string;
  output_path?: string;
  config?: Record<string, unknown>;
  description?: string;
  language?: string;
  file_count: number;
  graph_node_count: number;
  graph_edge_count: number;
  last_indexed_at?: string;
  created_at: string;
  updated_at: string;
  // computed on frontend
  status: 'ready' | 'indexing' | 'new' | 'error';
}

export interface IndexStatus {
  project_id: string;
  status: 'started' | 'running' | 'completed' | 'failed';
  task_id?: string;
  message: string;
}

// Raw backend graph types
export interface GraphNodeRaw {
  id: string;
  project_id: string;
  source_file_id?: string;
  node_type: string;
  qualified_name: string;
  display_name: string;
  line_start?: number;
  line_end?: number;
  signature?: string;
  docstring?: string;
  complexity?: number;
  metadata?: Record<string, unknown>;
}

export interface GraphEdgeRaw {
  id: string;
  project_id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: string;
  weight?: number;
  metadata?: Record<string, unknown>;
  llm_annotation?: string;
}

export interface GraphDataRaw {
  nodes: GraphNodeRaw[];
  edges: GraphEdgeRaw[];
  stats: Record<string, number>;
}

// Frontend-friendly graph types (used by Cytoscape)
export interface GraphNode {
  id: string;
  label: string;
  type: 'file' | 'class' | 'function' | 'module' | 'external' | 'method' | 'directory' | 'variable';
  file_path?: string;
  line_start?: number;
  line_end?: number;
  summary?: string;
  doc?: string;
  metrics?: Record<string, number>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: 'imports' | 'calls' | 'inherits' | 'composes' | 'decorates' | 'defines' | 'contains';
  weight?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// Source files (matches SourceFileOut)
export interface FileInfo {
  id: string;
  project_id: string;
  relative_path: string;
  content_hash?: string;
  line_count: number;
  token_estimate: number;
  language?: string;
  last_analyzed_at?: string;
  last_documented_at?: string;
  status: string;
  documentation_md?: string;
}

export interface FileSource {
  content: string;
  language: string;
  path: string;
  highlights?: Array<{ start: number; end: number; color?: string }>;
}

export interface DocNode {
  path: string;
  name: string;
  type: string;
  children?: DocNode[];
  has_doc: boolean;
  content?: string;
}

export interface Conversation {
  id: string;
  project_id: string;
  title?: string;
  scope?: string;
  pinned_files?: string[];
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  references?: Reference[];
  graph_highlights?: string[];
  suggestions?: string[];
  cost?: number;
  created_at: string;
}

export interface Reference {
  file: string;
  line?: number;
  snippet?: string;
}

export interface SSEEvent {
  type: 'token' | 'reference' | 'graph_highlight' | 'done' | 'suggestions' | 'error' | 'context_used';
  content?: string;
  file?: string;
  source?: string;
  line?: number;
  nodes?: string[];
  cost?: number;
  questions?: string[];
  suggestions?: string[];
  message?: string;
  message_id?: string;
}

export interface Settings {
  models: Record<string, string>;
  api_keys: Record<string, string>;
  webhooks: string[];
  agent: { enabled: boolean; model?: string; max_tokens?: number };
  theme: 'dark' | 'light' | 'system';
}

export interface TraceResult {
  path: GraphNode[];
  edges: GraphEdge[];
}

export interface ImpactResult {
  affected: GraphNode[];
  edges: GraphEdge[];
  risk_level: 'low' | 'medium' | 'high';
}

export interface DependencyInfo {
  upstream: Array<{ node: GraphNode; edge_type: string }>;
  downstream: Array<{ node: GraphNode; edge_type: string }>;
}

// Helper to transform raw backend graph data to frontend format
export function transformGraphData(raw: GraphDataRaw): GraphData {
  const nodeMap = new Map<string, string>(); // uuid -> qualified_name

  const nodes: GraphNode[] = raw.nodes.map((n) => {
    nodeMap.set(n.id, n.qualified_name);
    return {
      id: n.id,
      label: n.display_name,
      type: (n.node_type === 'class_' ? 'class' : n.node_type) as GraphNode['type'],
      file_path: n.qualified_name,
      line_start: n.line_start,
      line_end: n.line_end,
      summary: n.docstring,
      doc: n.signature,
    };
  });

  const edges: GraphEdge[] = raw.edges.map((e) => ({
    id: e.id,
    source: e.source_node_id,
    target: e.target_node_id,
    type: e.edge_type as GraphEdge['type'],
    weight: e.weight,
  }));

  return { nodes, edges };
}

// Helper to derive project status from backend data
export function deriveProjectStatus(project: Omit<Project, 'status'>): Project['status'] {
  if (project.last_indexed_at && project.file_count > 0) return 'ready';
  if (project.file_count === 0 && !project.last_indexed_at) return 'new';
  return 'new';
}
