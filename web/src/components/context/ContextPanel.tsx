import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useUIStore } from '@/stores/uiStore';
import { SourceView } from './SourceView';
import { GraphView } from './GraphView';
import { DocsTree } from './DocsTree';
import { DependencyView } from './DependencyView';
import { ExamplesView } from './ExamplesView';
import { Code, GitFork, BookOpen, ArrowUpDown, Lightbulb } from 'lucide-react';

export function ContextPanel() {
  const { activeContextTab, setActiveContextTab } = useUIStore();

  return (
    <div className="h-full flex flex-col bg-card/50">
      <Tabs value={activeContextTab} onValueChange={setActiveContextTab} className="flex flex-col h-full">
        <TabsList className="w-full justify-start rounded-none border-b border-border bg-transparent h-10 px-2">
          <TabsTrigger value="source" className="text-xs gap-1.5 data-[state=active]:bg-muted">
            <Code className="w-3.5 h-3.5" /> Source
          </TabsTrigger>
          <TabsTrigger value="graph" className="text-xs gap-1.5 data-[state=active]:bg-muted">
            <GitFork className="w-3.5 h-3.5" /> Graph
          </TabsTrigger>
          <TabsTrigger value="docs" className="text-xs gap-1.5 data-[state=active]:bg-muted">
            <BookOpen className="w-3.5 h-3.5" /> Docs
          </TabsTrigger>
          <TabsTrigger value="deps" className="text-xs gap-1.5 data-[state=active]:bg-muted">
            <ArrowUpDown className="w-3.5 h-3.5" /> Deps
          </TabsTrigger>
          <TabsTrigger value="examples" className="text-xs gap-1.5 data-[state=active]:bg-muted">
            <Lightbulb className="w-3.5 h-3.5" /> Examples
          </TabsTrigger>
        </TabsList>
        <TabsContent value="source" className="flex-1 overflow-hidden m-0">
          <SourceView />
        </TabsContent>
        <TabsContent value="graph" className="flex-1 overflow-hidden m-0">
          <GraphView />
        </TabsContent>
        <TabsContent value="docs" className="flex-1 overflow-hidden m-0">
          <DocsTree />
        </TabsContent>
        <TabsContent value="deps" className="flex-1 overflow-hidden m-0">
          <DependencyView />
        </TabsContent>
        <TabsContent value="examples" className="flex-1 overflow-hidden m-0">
          <ExamplesView />
        </TabsContent>
      </Tabs>
    </div>
  );
}
