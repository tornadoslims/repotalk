import { useState } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const models = [
  { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6' },
  { id: 'claude-opus-4-6', name: 'Claude Opus 4.6' },
  { id: 'claude-haiku-4-5', name: 'Claude Haiku 4.5' },
  { id: 'gpt-4o', name: 'GPT-4o' },
  { id: 'gpt-4o-mini', name: 'GPT-4o Mini' },
];

const phases = [
  { key: 'analysis', label: 'Code Analysis', desc: 'AST parsing and graph extraction' },
  { key: 'documentation', label: 'Documentation', desc: 'Generating documentation at all levels' },
  { key: 'chat', label: 'Chat / Q&A', desc: 'Interactive chat responses' },
  { key: 'rollup', label: 'Rollup', desc: 'Summarizing and rolling up documentation' },
];

export function ModelsConfig() {
  const [selectedModels, setSelectedModels] = useState<Record<string, string>>({
    analysis: 'claude-haiku-4-5',
    documentation: 'claude-sonnet-4-6',
    chat: 'claude-sonnet-4-6',
    rollup: 'claude-sonnet-4-6',
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Model Configuration</CardTitle>
        <CardDescription>Select which model to use for each processing phase</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {phases.map((phase) => (
          <div key={phase.key} className="flex items-center justify-between">
            <div>
              <Label className="text-sm">{phase.label}</Label>
              <p className="text-xs text-muted-foreground">{phase.desc}</p>
            </div>
            <Select
              value={selectedModels[phase.key]}
              onValueChange={(v) => setSelectedModels({ ...selectedModels, [phase.key]: v })}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {models.map((m) => (
                  <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
