import { useUIStore } from '@/stores/uiStore';
import { useCallback, useRef, useState } from 'react';
import { cn } from '@/lib/utils';

interface ResizablePanesProps {
  left: React.ReactNode;
  right: React.ReactNode;
  className?: string;
}

export function ResizablePanes({ left, right, className }: ResizablePanesProps) {
  const { leftPaneWidth, setLeftPaneWidth } = useUIStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);

    const onMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setLeftPaneWidth(Math.max(30, Math.min(80, pct)));
    };

    const onMouseUp = () => {
      setIsDragging(false);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }, [setLeftPaneWidth]);

  return (
    <div ref={containerRef} className={cn('flex flex-1 overflow-hidden', className)}>
      <div style={{ width: `${leftPaneWidth}%` }} className="overflow-hidden flex flex-col">
        {left}
      </div>
      <div
        onMouseDown={handleMouseDown}
        className={cn(
          'w-1 cursor-col-resize hover:bg-primary/50 transition-colors shrink-0',
          isDragging ? 'bg-primary' : 'bg-border'
        )}
      />
      <div style={{ width: `${100 - leftPaneWidth}%` }} className="overflow-hidden flex flex-col">
        {right}
      </div>
    </div>
  );
}
