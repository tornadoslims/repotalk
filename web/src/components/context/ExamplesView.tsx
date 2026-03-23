import { ScrollArea } from '@/components/ui/scroll-area';
import { CodeBlock } from '@/components/shared/CodeBlock';
import { Badge } from '@/components/ui/badge';
import { TestTube, Code, Copy } from 'lucide-react';

const sampleExamples = [
  {
    id: '1',
    title: 'Test: authenticate valid user',
    type: 'test',
    file: 'tests/test_auth.py',
    code: `def test_authenticate_valid_user():
    """Test successful authentication."""
    user = create_test_user("testuser", "password123")
    result = authenticate("testuser", "password123")
    assert result is not None
    assert result.username == "testuser"`,
    similarity: 0.95,
  },
  {
    id: '2',
    title: 'Test: authenticate invalid password',
    type: 'test',
    file: 'tests/test_auth.py',
    code: `def test_authenticate_invalid_password():
    """Test authentication with wrong password."""
    create_test_user("testuser", "password123")
    result = authenticate("testuser", "wrongpassword")
    assert result is None`,
    similarity: 0.92,
  },
  {
    id: '3',
    title: 'Similar: API key authentication',
    type: 'pattern',
    file: 'api_auth.py',
    code: `def authenticate_api_key(api_key: str) -> User | None:
    """Authenticate using API key."""
    db = get_db()
    key = db.query(ApiKey).filter(ApiKey.key == api_key).first()
    if not key or key.expired:
        return None
    return key.user`,
    similarity: 0.87,
  },
];

export function ExamplesView() {
  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        <div className="text-sm text-muted-foreground">
          Related code patterns and tests for the current context
        </div>
        {sampleExamples.map((example) => (
          <div key={example.id} className="border border-border rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 bg-muted/30 border-b border-border">
              <div className="flex items-center gap-2">
                {example.type === 'test' ? (
                  <TestTube className="w-3.5 h-3.5 text-green-400" />
                ) : (
                  <Code className="w-3.5 h-3.5 text-blue-400" />
                )}
                <span className="text-sm font-medium">{example.title}</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-[10px]">
                  {Math.round(example.similarity * 100)}% match
                </Badge>
                <button
                  className="text-muted-foreground hover:text-foreground transition-colors"
                  onClick={() => navigator.clipboard.writeText(example.code)}
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            <CodeBlock code={example.code} language="python" filename={example.file} />
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}
