import type { GraphNode } from '@/api/types';
import { NODE_COLORS } from '@/lib/constants';

interface GraphTooltipProps {
  node: GraphNode;
  x: number;
  y: number;
}

export function GraphTooltip({ node, x, y }: GraphTooltipProps) {
  return (
    <div
      className="graph-tooltip bg-card border border-border rounded-lg p-3 shadow-lg max-w-[250px]"
      style={{ left: x + 15, top: y - 10 }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: NODE_COLORS[node.type] }} />
        <span className="text-sm font-medium truncate">{node.label}</span>
      </div>
      <span className="text-xs text-muted-foreground capitalize">{node.type}</span>
      {node.summary && (
        <p className="text-xs text-muted-foreground mt-1.5 line-clamp-3">{node.summary}</p>
      )}
    </div>
  );
}
