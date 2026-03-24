import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  onReferenceClick?: (file: string, line?: number) => void;
}

export function MarkdownRenderer({ content, className, onReferenceClick }: MarkdownRendererProps) {
  const processedContent = content.replace(
    /\[([^\]]+?\.[\w]+):(\d+)\]/g,
    '[$1:$2](ref:$1:$2)'
  );

  return (
    <div className={cn('max-w-none text-sm text-foreground [&_h1]:text-lg [&_h1]:font-bold [&_h1]:mt-4 [&_h1]:mb-2 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-3 [&_h2]:mb-1.5 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mt-2 [&_h3]:mb-1 [&_p]:my-1.5 [&_p]:leading-relaxed [&_ul]:my-1.5 [&_ul]:pl-5 [&_ul]:list-disc [&_ol]:my-1.5 [&_ol]:pl-5 [&_ol]:list-decimal [&_li]:my-0.5 [&_strong]:font-semibold [&_blockquote]:border-l-2 [&_blockquote]:border-primary/50 [&_blockquote]:pl-3 [&_blockquote]:my-2 [&_blockquote]:text-muted-foreground [&_hr]:my-3 [&_hr]:border-border', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }: { href?: string; children?: ReactNode }) => {
            if (href?.startsWith('ref:')) {
              const parts = href.slice(4).split(':');
              const file = parts[0];
              const line = parts[1] ? parseInt(parts[1]) : undefined;
              return (
                <button
                  onClick={() => onReferenceClick?.(file, line)}
                  className="text-primary hover:text-primary/80 underline underline-offset-2 font-mono text-xs bg-primary/10 px-1 py-0.5 rounded"
                >
                  {children}
                </button>
              );
            }
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                {children}
              </a>
            );
          },
          code: ({ className: codeClassName, children, ...props }: { className?: string; children?: ReactNode }) => {
            const isInline = !codeClassName;
            if (isInline) {
              return (
                <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                  {children}
                </code>
              );
            }
            return (
              <code className={cn(codeClassName, 'block bg-card p-4 rounded-lg text-sm font-mono overflow-x-auto')} {...props}>
                {children}
              </code>
            );
          },
          pre: ({ children }: { children?: ReactNode }) => (
            <pre className="bg-card border border-border rounded-lg overflow-hidden my-3">{children}</pre>
          ),
          table: ({ children }: { children?: ReactNode }) => (
            <div className="overflow-x-auto my-3">
              <table className="w-full border-collapse border border-border text-sm">{children}</table>
            </div>
          ),
          th: ({ children }: { children?: ReactNode }) => (
            <th className="border border-border bg-muted px-3 py-2 text-left font-medium">{children}</th>
          ),
          td: ({ children }: { children?: ReactNode }) => (
            <td className="border border-border px-3 py-2">{children}</td>
          ),
        }}
      />
    </div>
  );
}
