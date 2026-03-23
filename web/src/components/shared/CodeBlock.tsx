import { cn } from '@/lib/utils';

interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  highlights?: Array<{ start: number; end: number }>;
  className?: string;
  onLineClick?: (line: number) => void;
}

export function CodeBlock({ code, language, filename, highlights = [], className, onLineClick }: CodeBlockProps) {
  const lines = code.split('\n');

  const isHighlighted = (lineNum: number) =>
    highlights.some((h) => lineNum >= h.start && lineNum <= h.end);

  return (
    <div className={cn('rounded-lg border border-border bg-card overflow-hidden', className)}>
      {filename && (
        <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-muted/50 text-sm text-muted-foreground">
          <span className="font-mono">{filename}</span>
          {language && <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">{language}</span>}
        </div>
      )}
      <div className="overflow-x-auto">
        <pre className="text-sm font-mono p-4">
          {lines.map((line, i) => {
            const lineNum = i + 1;
            return (
              <div
                key={i}
                className={cn(
                  'flex hover:bg-muted/30 transition-colors',
                  isHighlighted(lineNum) && 'bg-primary/10 border-l-2 border-primary',
                  onLineClick && 'cursor-pointer'
                )}
                onClick={() => onLineClick?.(lineNum)}
              >
                <span className="select-none text-muted-foreground w-12 text-right pr-4 shrink-0">
                  {lineNum}
                </span>
                <span className="flex-1 whitespace-pre">{line || ' '}</span>
              </div>
            );
          })}
        </pre>
      </div>
    </div>
  );
}
