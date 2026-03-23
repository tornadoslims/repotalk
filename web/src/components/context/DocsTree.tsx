import { useState } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { ChevronRight, ChevronDown, FileText, FolderOpen, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
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

export function DocsTree() {
  const [selectedDoc, setSelectedDoc] = useState<DocNode | null>(null);
  const [search, setSearch] = useState('');

  // Empty state placeholder - will be populated by API data
  const emptyDocs: DocNode[] = [];

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
            {emptyDocs.length === 0 ? (
              <div className="p-4 text-center text-xs text-muted-foreground">
                Index the project to generate documentation.
              </div>
            ) : (
              emptyDocs.map((doc) => (
                <TreeNode key={doc.path} node={doc} depth={0} selectedPath={selectedDoc?.path || null} onSelect={setSelectedDoc} />
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Content area */}
      <ScrollArea className="flex-1">
        {selectedDoc?.content ? (
          <div className="p-4">
            <MarkdownRenderer content={selectedDoc.content} />
            <div className="mt-4 text-xs text-muted-foreground">
              Source: <span className="font-mono text-primary">{selectedDoc.path}</span>
            </div>
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
