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
  const [indexProgress, setIndexProgress] = useState(0);
  const [filesDone, setFilesDone] = useState(0);
  const [filesTotal, setFilesTotal] = useState(0);

  useEffect(() => {
    if (projectId) {
      if (!currentProject || currentProject.id !== projectId) {
        const project = projects.find((p) => p.id === projectId);
        if (project) {
          setCurrentProject(project);
        } else {
          api.getProject(projectId).then(setCurrentProject).catch(console.error);
        }
      }
      loadFiles(projectId);
      loadGraph(projectId);
      loadConversations(projectId);

      // Check if already indexing on mount
      api.getIndexStatus(projectId).then((status) => {
        if (status.status === 'running') {
          setIndexing(true);
          setIndexMessage(status.message || 'Indexing in progress...');
          setIndexProgress(status.progress || 0);
          startPolling(projectId);
        }
      }).catch(() => {});
    }
  }, [projectId]);

  const startPolling = (pid: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await api.getIndexStatus(pid);
        setIndexMessage(status.message || status.phase || 'Indexing...');
        setIndexProgress(status.progress || 0);
        setFilesDone(status.files_done || 0);
        setFilesTotal(status.files_total || 0);

        if (status.status === 'completed' || status.phase === 'complete') {
          clearInterval(interval);
          setIndexing(false);
          setIndexMessage('Indexing complete!');
          setIndexProgress(1);
          // Reload everything
          loadFiles(pid);
          loadGraph(pid);
          api.getProject(pid).then(setCurrentProject).catch(console.error);
        } else if (status.phase === 'error') {
          clearInterval(interval);
          setIndexing(false);
          setIndexMessage('Indexing failed — check server logs');
          setIndexProgress(0);
        }
      } catch {
        // Keep polling
      }
    }, 2000);

    // Also try WebSocket for faster updates
    try {
      const ws = new WebSocket(`ws://${window.location.hostname}:8420/ws/project/${pid}`);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === 'index_progress') {
            setIndexMessage(data.message || data.phase);
            setIndexProgress(data.progress || 0);
            if (data.files_done !== undefined) setFilesDone(data.files_done);
            if (data.files_total !== undefined) setFilesTotal(data.files_total);
            if (data.phase === 'complete' || data.phase === 'error') {
              clearInterval(interval);
              setIndexing(data.phase !== 'complete');
              ws.close();
              if (data.phase === 'complete') {
                loadFiles(pid);
                loadGraph(pid);
                api.getProject(pid).then(setCurrentProject).catch(console.error);
              }
            }
          }
        } catch { /* ignore parse errors */ }
      };
      ws.onerror = () => ws.close();
    } catch {
      // WebSocket not available, polling handles it
    }

    return () => clearInterval(interval);
  };

  const handleIndex = async () => {
    if (!projectId) return;
    setIndexing(true);
    setIndexMessage('Starting indexing...');
    setIndexProgress(0);
    setFilesDone(0);
    setFilesTotal(0);
    const status = await indexProject(projectId);
    if (status) {
      setIndexMessage(status.message);
      startPolling(projectId);
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
        <div className="border-b border-border bg-muted/50">
          <div className="px-4 py-2 flex items-center gap-3">
            {indexing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-primary flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className="text-sm truncate block">{indexMessage || 'Indexing...'}</span>
                  {filesTotal > 0 && (
                    <span className="text-xs text-muted-foreground">{filesDone} / {filesTotal} files</span>
                  )}
                </div>
                <span className="text-xs text-muted-foreground flex-shrink-0">
                  {Math.round(indexProgress * 100)}%
                </span>
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
          {indexing && (
            <div className="h-1 bg-muted">
              <div
                className="h-full bg-primary transition-all duration-500 ease-out"
                style={{ width: `${Math.round(indexProgress * 100)}%` }}
              />
            </div>
          )}
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
