import { useMemo } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useGraphStore } from '@/stores/graphStore';
import { Badge } from '@/components/ui/badge';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { NODE_COLORS } from '@/lib/constants';
import type { GraphNode } from '@/api/types';

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
  const { selectedNode, graphData } = useGraphStore();

  const { upstream, downstream } = useMemo(() => {
    if (!selectedNode || !graphData) return { upstream: [], downstream: [] };

    const nodeMap = new Map(graphData.nodes.map((n) => [n.id, n]));

    // Upstream: edges where this node is the target (things that depend on this)
    const upstream = graphData.edges
      .filter((e) => e.target === selectedNode.id)
      .map((e) => ({ node: nodeMap.get(e.source)!, edge_type: e.type }))
      .filter((e) => e.node);

    // Downstream: edges where this node is the source (things this depends on)
    const downstream = graphData.edges
      .filter((e) => e.source === selectedNode.id)
      .map((e) => ({ node: nodeMap.get(e.target)!, edge_type: e.type }))
      .filter((e) => e.node);

    return { upstream, downstream };
  }, [selectedNode, graphData]);

  return (
    <div className="h-full flex flex-col">
      {selectedNode ? (
        <div className="px-3 py-2 border-b border-border text-sm">
          Dependencies for <span className="font-mono text-primary">{selectedNode.label}</span>
        </div>
      ) : (
        <div className="px-3 py-2 border-b border-border text-sm text-muted-foreground">
          Select a node in the graph to see its dependencies
        </div>
      )}
      <div className="flex-1 flex">
        <DepColumn title="Upstream (depends on this)" icon={<ArrowUp className="w-4 h-4 text-green-400" />} items={upstream} />
        <div className="w-px bg-border" />
        <DepColumn title="Downstream (this depends on)" icon={<ArrowDown className="w-4 h-4 text-blue-400" />} items={downstream} />
      </div>
    </div>
  );
}
