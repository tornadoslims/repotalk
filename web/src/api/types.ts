export interface Project {
  id: string;
  name: string;
  path: string;
  description?: string;
  language?: string;
  file_count: number;
  graph_node_count: number;
  last_updated: string;
  status: 'ready' | 'analyzing' | 'error';
  created_at: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'file' | 'class' | 'function' | 'module' | 'external';
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
  type: 'imports' | 'calls' | 'inherits' | 'composes' | 'decorates';
  weight?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface FileInfo {
  id: string;
  path: string;
  language: string;
  line_count: number;
  size: number;
  last_modified: string;
}

export interface FileSource {
  content: string;
  language: string;
  path: string;
  highlights?: Array<{ start: number; end: number; color?: string }>;
}

export interface DocNode {
  id: string;
  title: string;
  level: 'system' | 'module' | 'component' | 'function';
  content: string;
  children?: DocNode[];
  file_path?: string;
}

export interface Conversation {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
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
  type: 'token' | 'reference' | 'graph_highlight' | 'done' | 'suggestions' | 'error';
  content?: string;
  file?: string;
  line?: number;
  nodes?: string[];
  cost?: number;
  questions?: string[];
  message?: string;
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
