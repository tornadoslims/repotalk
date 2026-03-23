import { NODE_COLORS, EDGE_STYLES } from '@/lib/constants';

export function GraphLegend() {
  return (
    <div className="absolute bottom-3 left-3 bg-card/90 backdrop-blur border border-border rounded-lg p-2.5 text-xs">
      <div className="font-medium text-muted-foreground mb-1.5">Legend</div>
      <div className="space-y-1">
        <div className="font-medium text-muted-foreground text-[10px] uppercase tracking-wider">Nodes</div>
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
            <span className="capitalize text-foreground">{type}</span>
          </div>
        ))}
        <div className="font-medium text-muted-foreground text-[10px] uppercase tracking-wider mt-2">Edges</div>
        {Object.entries(EDGE_STYLES).map(([type, style]) => (
          <div key={type} className="flex items-center gap-2">
            <span className="w-4 h-0.5 rounded shrink-0" style={{ backgroundColor: style.color, borderStyle: style.style === 'dashed' ? 'dashed' : style.style === 'dotted' ? 'dotted' : 'solid' }} />
            <span className="text-foreground">{style.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
