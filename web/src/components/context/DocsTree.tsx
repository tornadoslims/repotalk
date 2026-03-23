import { useState } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { ChevronRight, ChevronDown, FileText, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DocNode } from '@/api/types';

const sampleDocs: DocNode[] = [
  {
    id: '1',
    title: 'System Overview',
    level: 'system',
    content: '# RepoTalk System\n\nRepoTalk is an AI-powered codebase intelligence platform that analyzes code structure, generates documentation, and provides an interactive chat interface for querying codebases.\n\n## Key Components\n- **AST Analyzer**: Parses source code into abstract syntax trees\n- **Knowledge Graph**: Maps relationships between code entities\n- **LLM Documenter**: Generates documentation at multiple levels\n- **Chat Interface**: RAG-powered conversational interface',
    children: [
      {
        id: '2',
        title: 'Authentication Module',
        level: 'module',
        content: '## Authentication\n\nHandles user authentication using JWT tokens.\n\n### Functions\n- `hash_password()` - SHA-256 password hashing\n- `verify_password()` - Password verification\n- `create_access_token()` - JWT token generation\n- `authenticate()` - User authentication\n- `login()` - Login flow with session creation',
        children: [
          {
            id: '3',
            title: 'authenticate()',
            level: 'function',
            content: '### authenticate(username, password)\n\nAuthenticates a user against the database.\n\n**Parameters:**\n- `username: str` - The username\n- `password: str` - The plain text password\n\n**Returns:** `User | None`\n\n**Calls:** `get_db()`, `verify_password()`',
            file_path: 'auth.py',
          },
          {
            id: '4',
            title: 'login()',
            level: 'function',
            content: '### login(username, password)\n\nPerforms login and returns access token.\n\n**Raises:** `ValueError` if credentials invalid.\n\n**Returns:** `dict` with `access_token` and `token_type`',
            file_path: 'auth.py',
          },
        ],
      },
      {
        id: '5',
        title: 'Models Module',
        level: 'module',
        content: '## Data Models\n\nDefines the core data models used throughout the system.\n\n### Classes\n- `User` - User account model\n- `Session` - Authentication session model',
        children: [
          {
            id: '6',
            title: 'User',
            level: 'component',
            content: '### User\n\nUser account model with fields:\n- `id: int`\n- `username: str`\n- `email: str`\n- `hashed_password: str`\n- `created_at: datetime`\n\n**Properties:** `is_active`',
            file_path: 'models.py',
          },
        ],
      },
    ],
  },
];

interface TreeNodeProps {
  node: DocNode;
  depth: number;
  selectedId: string | null;
  onSelect: (node: DocNode) => void;
}

function TreeNode({ node, depth, selectedId, onSelect }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;

  const levelColors: Record<string, string> = {
    system: 'text-primary',
    module: 'text-blue-400',
    component: 'text-green-400',
    function: 'text-purple-400',
  };

  return (
    <div>
      <button
        onClick={() => {
          if (hasChildren) setExpanded(!expanded);
          onSelect(node);
        }}
        className={cn(
          'w-full text-left flex items-center gap-1.5 py-1.5 px-2 rounded text-sm hover:bg-muted/50 transition-colors',
          selectedId === node.id && 'bg-primary/10 text-primary'
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {hasChildren ? (
          expanded ? <ChevronDown className="w-3.5 h-3.5 shrink-0 text-muted-foreground" /> : <ChevronRight className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
        ) : (
          <FileText className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
        )}
        <span className={cn('truncate', levelColors[node.level])}>{node.title}</span>
        <span className="text-[10px] text-muted-foreground ml-auto shrink-0">{node.level}</span>
      </button>
      {expanded && hasChildren && (
        <div>
          {node.children!.map((child) => (
            <TreeNode key={child.id} node={child} depth={depth + 1} selectedId={selectedId} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  );
}

export function DocsTree() {
  const [selectedDoc, setSelectedDoc] = useState<DocNode | null>(null);
  const [search, setSearch] = useState('');

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
            {sampleDocs.map((doc) => (
              <TreeNode key={doc.id} node={doc} depth={0} selectedId={selectedDoc?.id || null} onSelect={setSelectedDoc} />
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Content area */}
      <ScrollArea className="flex-1">
        {selectedDoc ? (
          <div className="p-4">
            <MarkdownRenderer content={selectedDoc.content} />
            {selectedDoc.file_path && (
              <div className="mt-4 text-xs text-muted-foreground">
                Source: <span className="font-mono text-primary">{selectedDoc.file_path}</span>
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
