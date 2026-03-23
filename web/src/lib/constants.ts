export const API_URL = '/api';

export const NODE_COLORS: Record<string, string> = {
  file: '#3b82f6',      // blue
  class: '#22c55e',     // green
  function: '#a855f7',  // purple
  module: '#f59e0b',    // amber
  external: '#6b7280',  // gray
};

export const EDGE_STYLES: Record<string, { color: string; style: string; width: number; label: string }> = {
  imports: { color: '#6b7280', style: 'dashed', width: 1, label: 'Imports' },
  calls: { color: '#3b82f6', style: 'solid', width: 2, label: 'Calls' },
  inherits: { color: '#22c55e', style: 'solid', width: 3, label: 'Inherits' },
  composes: { color: '#f97316', style: 'dotted', width: 2, label: 'Composes' },
  decorates: { color: '#a855f7', style: 'solid', width: 1, label: 'Decorates' },
};

export const FILE_ICONS: Record<string, string> = {
  py: '🐍',
  ts: '📘',
  tsx: '⚛️',
  js: '📒',
  jsx: '⚛️',
  rs: '🦀',
  go: '🐹',
  java: '☕',
  rb: '💎',
  css: '🎨',
  html: '🌐',
  json: '📋',
  md: '📝',
  yaml: '⚙️',
  yml: '⚙️',
  toml: '⚙️',
  default: '📄',
};
