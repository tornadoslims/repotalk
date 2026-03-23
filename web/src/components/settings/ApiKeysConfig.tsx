import { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Eye, EyeOff, Check } from 'lucide-react';

const providers = [
  { key: 'anthropic', label: 'Anthropic', placeholder: 'sk-ant-...' },
  { key: 'openai', label: 'OpenAI', placeholder: 'sk-...' },
];

export function ApiKeysConfig() {
  const [keys, setKeys] = useState<Record<string, string>>({ anthropic: '', openai: '' });
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});

  const handleSave = (provider: string) => {
    // In real app, call api.updateSettings()
    setSaved({ ...saved, [provider]: true });
    setTimeout(() => setSaved({ ...saved, [provider]: false }), 2000);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>API Keys</CardTitle>
        <CardDescription>Manage your LLM provider API keys</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {providers.map((p) => (
          <div key={p.key} className="space-y-1.5">
            <Label className="text-sm">{p.label}</Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  type={visible[p.key] ? 'text' : 'password'}
                  value={keys[p.key]}
                  onChange={(e) => setKeys({ ...keys, [p.key]: e.target.value })}
                  placeholder={p.placeholder}
                  className="pr-10"
                />
                <button
                  onClick={() => setVisible({ ...visible, [p.key]: !visible[p.key] })}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {visible[p.key] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <Button onClick={() => handleSave(p.key)} variant={saved[p.key] ? 'default' : 'outline'} className="w-20">
                {saved[p.key] ? <Check className="w-4 h-4" /> : 'Save'}
              </Button>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
