import { useState, useEffect, useMemo } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { ChevronRight, ChevronDown, FileText, FolderOpen, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useProjectStore } from '@/stores/projectStore';
import { api } from '@/api/client';
import type { DocNode } from '@/api/types';

interface TreeNodeProps {
  node: DocNode;
  depth: number;
  selectedPath: string | null;
  onSelect: (node: DocNode) => void;
}

function TreeNode({ node, depth, selectedPath, onSelect }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;
  const isDirectory = node.type === 'directory';

  return (
    <div>
      <button
        onClick={() => {
          if (hasChildren) setExpanded(!expanded);
          onSelect(node);
        }}
        className={cn(
          'w-full text-left flex items-center gap-1.5 py-1.5 px-2 rounded text-sm hover:bg-muted/50 transition-colors',
          selectedPath === node.path && 'bg-primary/10 text-primary'
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {hasChildren ? (
          expanded ? <ChevronDown className="w-3.5 h-3.5 shrink-0 text-muted-foreground" /> : <ChevronRight className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
        ) : isDirectory ? (
          <FolderOpen className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
        ) : (
          <FileText className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
        )}
        <span className={cn('truncate', isDirectory ? 'text-blue-400' : 'text-foreground')}>{node.name}</span>
        {node.has_doc && <span className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0 ml-auto" />}
      </button>
      {expanded && hasChildren && (
        <div>
          {node.children!.map((child) => (
            <TreeNode key={child.path} node={child} depth={depth + 1} selectedPath={selectedPath} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Build a nested tree from a flat array of DocNodes.
 * Each node has a 'path' like 'a/b/c'. We group by path segments
 * to create proper parent-child relationships.
 */
function buildNestedTree(flatNodes: DocNode[]): DocNode[] {
  // If nodes already have children populated, return as-is
  if (flatNodes.some((n) => n.children && n.children.length > 0)) {
    return flatNodes;
  }

  const root: DocNode[] = [];
  const map = new Map<string, DocNode>();

  // Sort by path so parents come before children
  const sorted = [...flatNodes].sort((a, b) => a.path.localeCompare(b.path));

  for (const node of sorted) {
    const parts = node.path.split('/');
    const parentPath = parts.slice(0, -1).join('/');

    // Ensure the node has a children array
    const treeNode: DocNode = { ...node, children: node.children || [] };
    map.set(node.path, treeNode);

    if (parentPath && map.has(parentPath)) {
      const parent = map.get(parentPath)!;
      if (!parent.children) parent.children = [];
      parent.children.push(treeNode);
    } else if (parentPath) {
      // Create intermediate directory nodes
      let currentPath = '';
      for (const part of parts.slice(0, -1)) {
        const prevPath = currentPath;
        currentPath = currentPath ? `${currentPath}/${part}` : part;
        if (!map.has(currentPath)) {
          const dirNode: DocNode = {
            path: currentPath,
            name: part,
            type: 'directory',
            children: [],
            has_doc: false,
          };
          map.set(currentPath, dirNode);
          if (prevPath && map.has(prevPath)) {
            map.get(prevPath)!.children!.push(dirNode);
          } else if (!prevPath) {
            root.push(dirNode);
          }
        }
      }
      map.get(parentPath)!.children!.push(treeNode);
    } else {
      root.push(treeNode);
    }
  }

  return root;
}

function filterTree(nodes: DocNode[], query: string): DocNode[] {
  if (!query) return nodes;
  const q = query.toLowerCase();
  return nodes
    .map((node) => {
      const childMatches = node.children ? filterTree(node.children, query) : [];
      const nameMatches = node.name.toLowerCase().includes(q) || node.path.toLowerCase().includes(q);
      if (nameMatches || childMatches.length > 0) {
        return { ...node, children: childMatches.length > 0 ? childMatches : node.children };
      }
      return null;
    })
    .filter(Boolean) as DocNode[];
}

export function DocsTree() {
  const [selectedDoc, setSelectedDoc] = useState<DocNode | null>(null);
  const [search, setSearch] = useState('');
  const [docs, setDocs] = useState<DocNode[]>([]);
  const [docContent, setDocContent] = useState<string | null>(null);
  const { currentProject } = useProjectStore();

  useEffect(() => {
    if (!currentProject?.id) return;
    api.getDocsTree(currentProject.id).then((data) => {
      setDocs(buildNestedTree(data));
    }).catch(() => setDocs([]));
  }, [currentProject?.id]);

  const filteredDocs = useMemo(() => filterTree(docs, search), [docs, search]);

  const handleSelect = async (node: DocNode) => {
    setSelectedDoc(node);
    if (node.content) {
      setDocContent(node.content);
    } else if (node.has_doc && currentProject?.id) {
      // Try to find the file and load its doc
      const files = useProjectStore.getState().files;
      const match = files.find(
        (f) => f.relative_path === node.path || f.relative_path.endsWith(node.path) || node.path.endsWith(f.relative_path)
      );
      if (match) {
        try {
          const doc = await api.getFileDoc(currentProject.id, match.id);
          setDocContent(doc.content || null);
        } catch {
          setDocContent(null);
        }
      } else if (match === undefined && node.type !== 'directory') {
        // Try loading doc content from documentation_md on file
        const fileMatch = files.find((f) => f.relative_path.replace(/\.[^.]+$/, '').endsWith(node.path.replace(/\.[^.]+$/, '')));
        if (fileMatch?.documentation_md) {
          setDocContent(fileMatch.documentation_md);
        } else {
          setDocContent(null);
        }
      } else {
        setDocContent(null);
      }
    } else {
      setDocContent(null);
    }
  };

  return (
    <div className="h-full flex">
      {/* Tree sidebar */}
      <div className="w-64 border-r border-border flex flex-col">
        <div className="p-2">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search docs..."
              className="h-8 pl-7 text-xs"
            />
          </div>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-1">
            {filteredDocs.length === 0 ? (
              <div className="p-4 text-center text-xs text-muted-foreground">
                {docs.length === 0
                  ? 'Index the project to generate documentation.'
                  : 'No matching docs found.'}
              </div>
            ) : (
              filteredDocs.map((doc) => (
                <TreeNode key={doc.path} node={doc} depth={0} selectedPath={selectedDoc?.path || null} onSelect={handleSelect} />
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Content area */}
      <ScrollArea className="flex-1">
        {docContent ? (
          <div className="p-4">
            <MarkdownRenderer content={docContent} />
            {selectedDoc && (
              <div className="mt-4 text-xs text-muted-foreground">
                Source: <span className="font-mono text-primary">{selectedDoc.path}</span>
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
            Select a documentation node to view
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
