import { useState } from 'react';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function AgentConfig() {
  const [enabled, setEnabled] = useState(false);
  const [model, setModel] = useState('claude-sonnet-4-6');
  const [maxTokens, setMaxTokens] = useState('4096');

  return (
    <Card>
      <CardHeader>
        <CardTitle>Coding Agent</CardTitle>
        <CardDescription>Configure the AI coding agent for automated fixes</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <Label>Enable Agent</Label>
            <p className="text-xs text-muted-foreground">Allow AI to suggest and apply code fixes</p>
          </div>
          <Switch checked={enabled} onCheckedChange={setEnabled} />
        </div>
        {enabled && (
          <>
            <div className="space-y-1.5">
              <Label className="text-sm">Agent Model</Label>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="claude-sonnet-4-6">Claude Sonnet 4.6</SelectItem>
                  <SelectItem value="claude-opus-4-6">Claude Opus 4.6</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-sm">Max Tokens</Label>
              <Input
                type="number"
                value={maxTokens}
                onChange={(e) => setMaxTokens(e.target.value)}
                className="w-32"
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
