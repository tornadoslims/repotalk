import { TopBar } from '@/components/layout/TopBar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ModelsConfig } from '@/components/settings/ModelsConfig';
import { ApiKeysConfig } from '@/components/settings/ApiKeysConfig';
import { UpdateConfig } from '@/components/settings/UpdateConfig';
import { AgentConfig } from '@/components/settings/AgentConfig';
import { UsageDashboard } from '@/components/settings/UsageDashboard';

export function Settings() {
  return (
    <div className="h-screen flex flex-col bg-background">
      <TopBar />
      <ScrollArea className="flex-1">
        <div className="max-w-3xl mx-auto p-6 space-y-6">
          <div>
            <h1 className="text-2xl font-bold">Settings</h1>
            <p className="text-sm text-muted-foreground">Configure your RepoTalk instance</p>
          </div>
          <ModelsConfig />
          <ApiKeysConfig />
          <AgentConfig />
          <UpdateConfig />
          <UsageDashboard />
        </div>
      </ScrollArea>
    </div>
  );
}
