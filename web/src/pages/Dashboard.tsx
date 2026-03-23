import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProjectStore } from '@/stores/projectStore';
import { useProject } from '@/hooks/useProject';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Plus, GitBranch, FileText, GitFork, Clock, ArrowRight, FolderOpen, Loader2, Play, AlertCircle } from 'lucide-react';

export function Dashboard() {
  const { projects, loading, error } = useProjectStore();
  const { loadProjects, createProject, indexProject, setCurrentProject } = useProject();
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [indexingIds, setIndexingIds] = useState<Set<string>>(new Set());
  const [formData, setFormData] = useState({
    name: '',
    source_path: '',
    description: '',
  });

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleProjectClick = (project: typeof projects[0]) => {
    setCurrentProject(project);
    navigate(`/project/${project.id}`);
  };

  const handleCreateProject = async () => {
    if (!formData.name || !formData.source_path) return;
    setCreating(true);
    try {
      const project = await createProject({
        name: formData.name,
        path: formData.source_path,
        description: formData.description,
      });
      if (project) {
        setDialogOpen(false);
        setFormData({ name: '', source_path: '', description: '' });
        await loadProjects();
        setCurrentProject(project);
        navigate(`/project/${project.id}`);
      }
    } finally {
      setCreating(false);
    }
  };

  const handleIndex = async (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation(); // Don't navigate to project
    setIndexingIds((prev) => new Set(prev).add(projectId));
    const status = await indexProject(projectId);
    if (status) {
      // Poll for completion
      const interval = setInterval(async () => {
        await loadProjects();
        // Simple check: reload projects to see updated stats
        setIndexingIds((prev) => {
          const next = new Set(prev);
          next.delete(projectId);
          return next;
        });
        clearInterval(interval);
      }, 10000);
    } else {
      setIndexingIds((prev) => {
        const next = new Set(prev);
        next.delete(projectId);
        return next;
      });
    }
  };

  const openDialog = () => setDialogOpen(true);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="max-w-5xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
                <GitBranch className="w-5 h-5 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">RepoTalk</h1>
                <p className="text-sm text-muted-foreground">AI-powered codebase intelligence</p>
              </div>
            </div>
            <Button className="gap-2" onClick={openDialog}>
              <Plus className="w-4 h-4" />
              New Project
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        <h2 className="text-lg font-semibold mb-4">Your Projects</h2>

        {/* Error banner */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
            <span className="text-xs text-muted-foreground ml-auto">Is the backend running on port 8420?</span>
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-4 w-60" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-4 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : projects.length === 0 ? (
          <Card className="text-center py-12">
            <CardContent>
              <FolderOpen className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">No projects yet</h3>
              <p className="text-sm text-muted-foreground mb-6">
                Add a codebase to start analyzing and chatting with your code
              </p>
              <Button className="gap-2" onClick={openDialog}>
                <Plus className="w-4 h-4" /> Add Your First Project
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {projects.map((project) => {
              const isIndexing = indexingIds.has(project.id) || project.status === 'indexing';
              return (
                <Card
                  key={project.id}
                  className="cursor-pointer hover:border-primary/50 transition-colors group"
                  onClick={() => handleProjectClick(project)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base flex items-center gap-2">
                        {project.name}
                        <Badge
                          variant={project.status === 'ready' ? 'default' : project.status === 'indexing' ? 'secondary' : 'outline'}
                          className="text-[10px]"
                        >
                          {project.status}
                        </Badge>
                      </CardTitle>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-xs gap-1"
                          disabled={isIndexing}
                          onClick={(e) => handleIndex(e, project.id)}
                          title="Index this project"
                        >
                          {isIndexing ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Play className="w-3 h-3" />
                          )}
                          {isIndexing ? 'Indexing...' : 'Index'}
                        </Button>
                        <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    </div>
                    <CardDescription className="truncate">{project.source_path}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium">{project.language || 'Python'}</span>
                      </span>
                      <span className="flex items-center gap-1">
                        <FileText className="w-3 h-3" /> {project.file_count || 0} files
                      </span>
                      <span className="flex items-center gap-1">
                        <GitFork className="w-3 h-3" /> {project.graph_node_count || 0} nodes
                      </span>
                      <span className="flex items-center gap-1 ml-auto">
                        <Clock className="w-3 h-3" />
                        {project.last_indexed_at
                          ? new Date(project.last_indexed_at).toLocaleDateString()
                          : 'not indexed'}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </main>

      {/* Create Project Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add New Project</DialogTitle>
            <DialogDescription>
              Point RepoTalk at a codebase to analyze it and build the knowledge graph.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Project Name</Label>
              <Input
                id="name"
                placeholder="my-project"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="path">Source Path</Label>
              <Input
                id="path"
                placeholder="/path/to/your/codebase"
                value={formData.source_path}
                onChange={(e) => setFormData({ ...formData, source_path: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                Absolute path to the root directory of the codebase
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Input
                id="description"
                placeholder="What is this codebase?"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateProject}
              disabled={!formData.name || !formData.source_path || creating}
              className="gap-2"
            >
              {creating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Create Project
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
