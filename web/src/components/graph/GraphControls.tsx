import { useGraphStore } from '@/stores/graphStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { EDGE_STYLES } from '@/lib/constants';
import { ZoomIn, ZoomOut, Maximize, Search } from 'lucide-react';
import { useState } from 'react';

interface GraphControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
}

export function GraphControls({ onZoomIn, onZoomOut, onFit }: GraphControlsProps) {
  const { layoutMode, setLayoutMode, edgeFilters, toggleEdgeFilter, searchQuery, setSearchQuery } = useGraphStore();
  const [showFilters, setShowFilters] = useState(false);

  return (
    <>
      {/* Top controls */}
      <div className="absolute top-3 left-3 flex items-center gap-2">
        <Select value={layoutMode} onValueChange={(v) => setLayoutMode(v as any)}>
          <SelectTrigger className="h-8 w-[140px] bg-card/90 backdrop-blur text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="fcose">Force Directed</SelectItem>
            <SelectItem value="circle">Circle</SelectItem>
            <SelectItem value="grid">Grid</SelectItem>
            <SelectItem value="breadthfirst">Hierarchy</SelectItem>
          </SelectContent>
        </Select>

        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search nodes..."
            className="h-8 w-[160px] pl-7 bg-card/90 backdrop-blur text-xs"
          />
        </div>

        <Button
          variant="outline"
          size="sm"
          className="h-8 text-xs bg-card/90 backdrop-blur"
          onClick={() => setShowFilters(!showFilters)}
        >
          Filters
        </Button>
      </div>

      {/* Edge filters panel */}
      {showFilters && (
        <div className="absolute top-12 left-3 bg-card/95 backdrop-blur border border-border rounded-lg p-3 space-y-2 min-w-[180px]">
          <span className="text-xs font-medium text-muted-foreground">Edge Types</span>
          {Object.entries(EDGE_STYLES).map(([type, style]) => (
            <div key={type} className="flex items-center justify-between">
              <Label className="flex items-center gap-2 text-xs cursor-pointer">
                <span className="w-3 h-1 rounded" style={{ backgroundColor: style.color }} />
                {style.label}
              </Label>
              <Switch
                checked={edgeFilters[type] !== false}
                onCheckedChange={() => toggleEdgeFilter(type)}
                className="scale-75"
              />
            </div>
          ))}
        </div>
      )}

      {/* Zoom controls */}
      <div className="absolute bottom-3 right-3 flex flex-col gap-1">
        <Button variant="outline" size="icon" className="h-8 w-8 bg-card/90 backdrop-blur" onClick={onZoomIn}>
          <ZoomIn className="w-4 h-4" />
        </Button>
        <Button variant="outline" size="icon" className="h-8 w-8 bg-card/90 backdrop-blur" onClick={onZoomOut}>
          <ZoomOut className="w-4 h-4" />
        </Button>
        <Button variant="outline" size="icon" className="h-8 w-8 bg-card/90 backdrop-blur" onClick={onFit}>
          <Maximize className="w-4 h-4" />
        </Button>
      </div>
    </>
  );
}
