import Editor from '@monaco-editor/react';
import { useUIStore } from '@/stores/uiStore';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export function SourceView() {
  const { theme, sourceTabs, activeSourceTab, setActiveSourceTab, removeSourceTab } = useUIStore();

  const currentTab = sourceTabs.find((t) => t.id === activeSourceTab);

  const handleEditorMount = (editor: any, monaco: any) => {
    if (!currentTab?.highlights) return;
    const decorations = currentTab.highlights.map((h) => ({
      range: new monaco.Range(h.startLine, 1, h.endLine, 1),
      options: {
        isWholeLine: true,
        className: 'highlighted-line',
        glyphMarginClassName: 'highlighted-glyph',
      },
    }));
    editor.createDecorationsCollection(decorations);
  };

  if (sourceTabs.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
        Click a reference in chat to view source code
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Tab bar */}
      <div className="flex items-center border-b border-border bg-muted/30 overflow-x-auto">
        {sourceTabs.map((tab) => (
          <div
            key={tab.id}
            role="tab"
            tabIndex={0}
            onClick={() => setActiveSourceTab(tab.id)}
            onKeyDown={(e) => e.key === 'Enter' && setActiveSourceTab(tab.id)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 text-xs border-r border-border shrink-0 group cursor-pointer',
              activeSourceTab === tab.id
                ? 'bg-card text-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            )}
          >
            <span className="font-mono">{tab.filename}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                removeSourceTab(tab.id);
              }}
              className="opacity-0 group-hover:opacity-100 hover:text-destructive transition-opacity"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>

      {/* Editor */}
      <div className="flex-1">
        {currentTab && (
          <Editor
            key={currentTab.id}
            height="100%"
            language={currentTab.language}
            value={currentTab.content}
            theme={theme === 'dark' ? 'vs-dark' : 'vs'}
            onMount={handleEditorMount}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              fontSize: 13,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              padding: { top: 8 },
              renderLineHighlight: 'all',
              smoothScrolling: true,
            }}
          />
        )}
      </div>
    </div>
  );
}
