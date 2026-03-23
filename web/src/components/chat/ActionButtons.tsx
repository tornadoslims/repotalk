import { Button } from '@/components/ui/button';
import { GitBranch, Wrench, Download, RefreshCw } from 'lucide-react';

interface ActionButtonsProps {
  messageId: string;
}

export function ActionButtons({ messageId }: ActionButtonsProps) {
  const handleAction = (action: string) => {
    // Show a toast or perform the action
    console.log(`Action: ${action} on message ${messageId}`);
  };

  return (
    <div className="flex items-center gap-1 mt-2">
      <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground hover:text-foreground" onClick={() => handleAction('trace')}>
        <GitBranch className="w-3 h-3 mr-1" /> Trace
      </Button>
      <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground hover:text-foreground" onClick={() => handleAction('fix')}>
        <Wrench className="w-3 h-3 mr-1" /> Fix This
      </Button>
      <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground hover:text-foreground" onClick={() => handleAction('export')}>
        <Download className="w-3 h-3 mr-1" /> Export
      </Button>
      <Button variant="ghost" size="sm" className="h-7 text-xs text-muted-foreground hover:text-foreground" onClick={() => handleAction('regenerate')}>
        <RefreshCw className="w-3 h-3 mr-1" /> Regen
      </Button>
    </div>
  );
}
