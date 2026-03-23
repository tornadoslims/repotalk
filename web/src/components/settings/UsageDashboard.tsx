import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const usageData = [
  { date: 'Today', tokens: 45230, cost: 0.0678, requests: 12 },
  { date: 'Yesterday', tokens: 128400, cost: 0.1926, requests: 34 },
  { date: 'This Week', tokens: 534000, cost: 0.801, requests: 142 },
  { date: 'This Month', tokens: 2145000, cost: 3.2175, requests: 567 },
];

export function UsageDashboard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Usage & Costs</CardTitle>
        <CardDescription>Token usage and cost breakdown</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {usageData.map((row) => (
            <div key={row.date} className="flex items-center justify-between py-2 border-b border-border last:border-0">
              <div>
                <span className="text-sm font-medium">{row.date}</span>
                <p className="text-xs text-muted-foreground">{row.requests} requests</p>
              </div>
              <div className="text-right">
                <span className="text-sm font-mono">${row.cost.toFixed(4)}</span>
                <p className="text-xs text-muted-foreground">{(row.tokens / 1000).toFixed(1)}K tokens</p>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 p-3 rounded-lg bg-muted/50 flex items-center justify-between">
          <span className="text-sm font-medium">Total This Month</span>
          <Badge variant="secondary" className="font-mono">${usageData[3].cost.toFixed(4)}</Badge>
        </div>
      </CardContent>
    </Card>
  );
}
