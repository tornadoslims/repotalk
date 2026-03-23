import { useProjectStore } from '@/stores/projectStore';
import { useGraphStore } from '@/stores/graphStore';
import { useChatStore } from '@/stores/chatStore';
import { FileText, GitFork, Clock, DollarSign, Wifi } from 'lucide-react';

export function StatusBar() {
  const { currentProject, files } = useProjectStore();
  const { graphData } = useGraphStore();
  const { totalCost } = useChatStore();

  return (
    <footer className="h-7 border-t border-border bg-card flex items-center justify-between px-4 text-xs text-muted-foreground shrink-0">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1">
          <FileText className="w-3 h-3" />
          {files.length || currentProject?.file_count || 0} files
        </span>
        <span className="flex items-center gap-1">
          <GitFork className="w-3 h-3" />
          {graphData?.nodes.length || currentProject?.graph_node_count || 0} nodes
          {graphData && ` · ${graphData.edges.length} edges`}
        </span>
      </div>
      <div className="flex items-center gap-4">
        {totalCost > 0 && (
          <span className="flex items-center gap-1">
            <DollarSign className="w-3 h-3" />
            ${totalCost.toFixed(4)}
          </span>
        )}
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {currentProject?.last_indexed_at
            ? new Date(currentProject.last_indexed_at).toLocaleString()
            : 'Not indexed'}
        </span>
        <span className="flex items-center gap-1">
          <Wifi className="w-3 h-3 text-green-500" />
          Connected
        </span>
      </div>
    </footer>
  );
}
