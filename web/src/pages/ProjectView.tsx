import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useProjectStore } from '@/stores/projectStore';
import { useProject } from '@/hooks/useProject';
import { useGraph } from '@/hooks/useGraph';
import { useChat } from '@/hooks/useChat';
import { TopBar } from '@/components/layout/TopBar';
import { StatusBar } from '@/components/layout/StatusBar';
import { ResizablePanes } from '@/components/layout/ResizablePanes';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { ContextPanel } from '@/components/context/ContextPanel';
import { Button } from '@/components/ui/button';
import { Play, Loader2, CheckCircle } from 'lucide-react';
import { api } from '@/api/client';

export function ProjectView() {
  const { projectId } = useParams<{ projectId: string }>();
  const { currentProject, projects } = useProjectStore();
  const { setCurrentProject, loadFiles, indexProject } = useProject();
  const { loadGraph } = useGraph();
  const { loadConversations } = useChat();
  const [indexing, setIndexing] = useState(false);
  const [indexMessage, setIndexMessage] = useState('');

  useEffect(() => {
    if (projectId) {
      // Set current project if not already set
      if (!currentProject || currentProject.id !== projectId) {
        const project = projects.find((p) => p.id === projectId);
        if (project) {
          setCurrentProject(project);
        } else {
          // Load from API if not in store
          api.getProject(projectId).then(setCurrentProject).catch(console.error);
        }
      }
      loadFiles(projectId);
      loadGraph(projectId);
      loadConversations(projectId);
    }
  }, [projectId]);

  const handleIndex = async () => {
    if (!projectId) return;
    setIndexing(true);
    setIndexMessage('Starting indexing...');
    const status = await indexProject(projectId);
    if (status) {
      setIndexMessage(status.message);
      // Set up WebSocket listener for progress
      try {
        const ws = new WebSocket(`ws://${window.location.hostname}:8420/ws/project/${projectId}`);
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.event === 'index_progress') {
              setIndexMessage(data.message || data.phase);
              if (data.phase === 'complete' || data.phase === 'error') {
                setIndexing(false);
                ws.close();
                // Reload data
                loadFiles(projectId);
                loadGraph(projectId);
                api.getProject(projectId).then(setCurrentProject).catch(console.error);
              }
            }
          } catch { /* ignore */ }
        };
        ws.onerror = () => {
          // Fallback: poll after a timeout
          setTimeout(async () => {
            setIndexing(false);
            setIndexMessage('');
            loadFiles(projectId);
            loadGraph(projectId);
          }, 30000);
        };
      } catch {
        // No WebSocket available, poll after timeout
        setTimeout(() => {
          setIndexing(false);
          setIndexMessage('');
          loadFiles(projectId);
          loadGraph(projectId);
        }, 30000);
      }
    } else {
      setIndexing(false);
      setIndexMessage('Failed to start indexing');
    }
  };

  const needsIndexing = currentProject && currentProject.status === 'new';

  return (
    <div className="h-screen flex flex-col bg-background">
      <TopBar />
      {/* Index banner */}
      {(needsIndexing || indexing || indexMessage) && (
        <div className="px-4 py-2 border-b border-border bg-muted/50 flex items-center gap-3">
          {indexing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-primary" />
              <span className="text-sm">{indexMessage || 'Indexing...'}</span>
            </>
          ) : indexMessage && indexMessage.includes('complete') ? (
            <>
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="text-sm text-green-600">{indexMessage}</span>
            </>
          ) : needsIndexing ? (
            <>
              <span className="text-sm text-muted-foreground">This project hasn't been indexed yet.</span>
              <Button size="sm" className="gap-1 h-7" onClick={handleIndex}>
                <Play className="w-3 h-3" />
                Index Now
              </Button>
            </>
          ) : null}
        </div>
      )}
      <ResizablePanes
        left={<ChatPanel />}
        right={<ContextPanel />}
      />
      <StatusBar />
    </div>
  );
}
