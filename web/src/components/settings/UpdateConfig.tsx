import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Trash2 } from 'lucide-react';

export function UpdateConfig() {
  const [webhooks, setWebhooks] = useState<string[]>(['https://github.com/webhook/123']);
  const [newWebhook, setNewWebhook] = useState('');
  const [watchEnabled, setWatchEnabled] = useState(true);
  const [watchInterval, setWatchInterval] = useState('300');

  const addWebhook = () => {
    if (newWebhook.trim()) {
      setWebhooks([...webhooks, newWebhook.trim()]);
      setNewWebhook('');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Update Settings</CardTitle>
        <CardDescription>Configure how your codebase stays in sync</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <Label>File Watcher</Label>
              <p className="text-xs text-muted-foreground">Automatically re-analyze on file changes</p>
            </div>
            <Switch checked={watchEnabled} onCheckedChange={setWatchEnabled} />
          </div>
          {watchEnabled && (
            <div className="space-y-1.5">
              <Label className="text-xs">Poll interval (seconds)</Label>
              <Input
                type="number"
                value={watchInterval}
                onChange={(e) => setWatchInterval(e.target.value)}
                className="w-32"
              />
            </div>
          )}
        </div>

        <div className="space-y-3">
          <Label>Webhooks</Label>
          <div className="space-y-2">
            {webhooks.map((wh, i) => (
              <div key={i} className="flex items-center gap-2">
                <Input value={wh} readOnly className="flex-1 text-sm font-mono" />
                <Button variant="ghost" size="icon" onClick={() => setWebhooks(webhooks.filter((_, j) => j !== i))}>
                  <Trash2 className="w-4 h-4 text-destructive" />
                </Button>
              </div>
            ))}
            <div className="flex gap-2">
              <Input
                value={newWebhook}
                onChange={(e) => setNewWebhook(e.target.value)}
                placeholder="https://..."
                className="flex-1"
                onKeyDown={(e) => e.key === 'Enter' && addWebhook()}
              />
              <Button variant="outline" onClick={addWebhook}>
                <Plus className="w-4 h-4 mr-1" /> Add
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
