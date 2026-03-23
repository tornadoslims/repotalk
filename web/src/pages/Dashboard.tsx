import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProjectStore } from '@/stores/projectStore';
import { useProject } from '@/hooks/useProject';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Plus, GitBranch, FileText, GitFork, Clock, ArrowRight } from 'lucide-react';

export function Dashboard() {
  const { projects, loading } = useProjectStore();
  const { loadProjects, setCurrentProject } = useProject();
  const navigate = useNavigate();

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleProjectClick = (project: typeof projects[0]) => {
    setCurrentProject(project);
    navigate(`/project/${project.id}`);
  };

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
            <Button className="gap-2">
              <Plus className="w-4 h-4" />
              New Project
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        <h2 className="text-lg font-semibold mb-4">Your Projects</h2>

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
              <GitBranch className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">No projects yet</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Add a codebase to start analyzing and chatting with your code
              </p>
              <Button className="gap-2">
                <Plus className="w-4 h-4" /> Add Your First Project
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {projects.map((project) => (
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
                        variant={project.status === 'ready' ? 'default' : project.status === 'analyzing' ? 'secondary' : 'destructive'}
                        className="text-[10px]"
                      >
                        {project.status}
                      </Badge>
                    </CardTitle>
                    <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                  <CardDescription>{project.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium">{project.language}</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <FileText className="w-3 h-3" /> {project.file_count} files
                    </span>
                    <span className="flex items-center gap-1">
                      <GitFork className="w-3 h-3" /> {project.graph_node_count} nodes
                    </span>
                    <span className="flex items-center gap-1 ml-auto">
                      <Clock className="w-3 h-3" /> {new Date(project.last_updated).toLocaleDateString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
