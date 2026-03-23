import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useProjectStore } from '@/stores/projectStore';
import { useUIStore } from '@/stores/uiStore';
import { useProject } from '@/hooks/useProject';
import { useGraph } from '@/hooks/useGraph';
import { useChat } from '@/hooks/useChat';
import { TopBar } from '@/components/layout/TopBar';
import { StatusBar } from '@/components/layout/StatusBar';
import { ResizablePanes } from '@/components/layout/ResizablePanes';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { ContextPanel } from '@/components/context/ContextPanel';

export function ProjectView() {
  const { projectId } = useParams<{ projectId: string }>();
  const { currentProject, projects } = useProjectStore();
  const { setCurrentProject } = useProject();
  const { loadFiles } = useProject();
  const { loadGraph } = useGraph();
  const { loadConversations } = useChat();

  useEffect(() => {
    if (projectId) {
      // Set current project if not already set
      if (!currentProject || currentProject.id !== projectId) {
        const project = projects.find((p) => p.id === projectId);
        if (project) setCurrentProject(project);
      }
      loadFiles(projectId);
      loadGraph(projectId);
      loadConversations(projectId);
    }
  }, [projectId]);

  return (
    <div className="h-screen flex flex-col bg-background">
      <TopBar />
      <ResizablePanes
        left={<ChatPanel />}
        right={<ContextPanel />}
      />
      <StatusBar />
    </div>
  );
}
