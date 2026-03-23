import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useEffect } from 'react';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Dashboard } from '@/pages/Dashboard';
import { ProjectView } from '@/pages/ProjectView';
import { Settings } from '@/pages/Settings';
import { useUIStore } from '@/stores/uiStore';

function AppInner() {
  const { theme } = useUIStore();

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/project/:projectId" element={<ProjectView />} />
      <Route path="/settings" element={<Settings />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <TooltipProvider>
        <AppInner />
      </TooltipProvider>
    </BrowserRouter>
  );
}
