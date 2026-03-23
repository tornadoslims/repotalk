import { useProjectStore } from '@/stores/projectStore';
import { useUIStore } from '@/stores/uiStore';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Settings, Sun, Moon, GitBranch, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';

export function TopBar() {
  const { projects, currentProject, setCurrentProject } = useProjectStore();
  const { theme, toggleTheme } = useUIStore();
  const navigate = useNavigate();

  return (
    <header className="h-14 border-b border-border bg-card flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-3">
        {/* Logo */}
        <button onClick={() => navigate('/')} className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <GitBranch className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-semibold text-foreground text-lg">RepoTalk</span>
        </button>

        {/* Separator */}
        <ChevronRight className="w-4 h-4 text-muted-foreground" />

        {/* Project selector */}
        <Select
          value={currentProject?.id || ''}
          onValueChange={(id) => {
            const project = projects.find((p) => p.id === id);
            if (project) {
              setCurrentProject(project);
              navigate(`/project/${project.id}`);
            }
          }}
        >
          <SelectTrigger className="w-[200px] h-9">
            <SelectValue placeholder="Select project..." />
          </SelectTrigger>
          <SelectContent>
            {projects.map((p) => (
              <SelectItem key={p.id} value={p.id}>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.status === 'ready' ? '#22c55e' : p.status === 'indexing' ? '#f59e0b' : '#6b7280' }} />
                  {p.name}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Scope breadcrumb */}
        {currentProject && (
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <ChevronRight className="w-3 h-3" />
            <span className="px-2 py-1 rounded bg-muted text-xs">{currentProject.language || 'Python'}</span>
            <span className="text-xs">{currentProject.file_count} files</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={toggleTheme} className="h-9 w-9">
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </Button>
        <Button variant="ghost" size="icon" onClick={() => navigate('/settings')} className="h-9 w-9">
          <Settings className="w-4 h-4" />
        </Button>
        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-sm font-medium text-primary">
          U
        </div>
      </div>
    </header>
  );
}
