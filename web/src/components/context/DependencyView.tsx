import { ScrollArea } from '@/components/ui/scroll-area';
import { useGraphStore } from '@/stores/graphStore';
import { Badge } from '@/components/ui/badge';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { NODE_COLORS } from '@/lib/constants';
import type { GraphNode } from '@/api/types';

const sampleUpstream: Array<{ node: GraphNode; edge_type: string }> = [
  { node: { id: '1', label: 'main.py', type: 'file' }, edge_type: 'imports' },
  { node: { id: '2', label: 'routes.py', type: 'file' }, edge_type: 'imports' },
  { node: { id: '3', label: 'middleware.py', type: 'file' }, edge_type: 'imports' },
];

const sampleDownstream: Array<{ node: GraphNode; edge_type: string }> = [
  { node: { id: '4', label: 'models.py', type: 'file' }, edge_type: 'imports' },
  { node: { id: '5', label: 'database', type: 'module' }, edge_type: 'composes' },
  { node: { id: '6', label: 'jwt', type: 'external' }, edge_type: 'imports' },
  { node: { id: '7', label: 'User', type: 'class' }, edge_type: 'calls' },
];

interface DepColumnProps {
  title: string;
  icon: React.ReactNode;
  items: Array<{ node: GraphNode; edge_type: string }>;
}

function DepColumn({ title, icon, items }: DepColumnProps) {
  return (
    <div className="flex-1 flex flex-col min-w-0">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border text-sm font-medium">
        {icon}
        {title}
        <Badge variant="secondary" className="text-[10px] ml-auto">{items.length}</Badge>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {items.length === 0 ? (
            <div className="text-xs text-muted-foreground p-3 text-center">No dependencies</div>
          ) : (
            items.map((item) => (
              <button
                key={item.node.id}
                className="w-full text-left flex items-center gap-2 px-3 py-2 rounded hover:bg-muted/50 transition-colors group"
              >
                <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: NODE_COLORS[item.node.type] }} />
                <span className="text-sm truncate flex-1">{item.node.label}</span>
                <span className="text-[10px] text-muted-foreground">{item.edge_type}</span>
              </button>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

export function DependencyView() {
  const { selectedNode } = useGraphStore();

  return (
    <div className="h-full flex flex-col">
      {selectedNode ? (
        <div className="px-3 py-2 border-b border-border text-sm">
          Dependencies for <span className="font-mono text-primary">{selectedNode.label}</span>
        </div>
      ) : (
        <div className="px-3 py-2 border-b border-border text-sm text-muted-foreground">
          Select a node to see dependencies (showing sample data)
        </div>
      )}
      <div className="flex-1 flex">
        <DepColumn title="Upstream (depends on this)" icon={<ArrowUp className="w-4 h-4 text-green-400" />} items={sampleUpstream} />
        <div className="w-px bg-border" />
        <DepColumn title="Downstream (this depends on)" icon={<ArrowDown className="w-4 h-4 text-blue-400" />} items={sampleDownstream} />
      </div>
    </div>
  );
}
