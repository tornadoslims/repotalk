import { useState } from 'react';
import Editor from '@monaco-editor/react';
import { useUIStore } from '@/stores/uiStore';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SourceTab {
  id: string;
  filename: string;
  content: string;
  language: string;
  highlights?: Array<{ startLine: number; endLine: number }>;
}

const sampleTabs: SourceTab[] = [
  {
    id: 'auth',
    filename: 'auth.py',
    content: `"""Authentication module for RepoTalk."""
import jwt
import hashlib
from datetime import datetime, timedelta
from models import User, Session
from database import get_db


SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(plain) == hashed


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate(username: str, password: str) -> User | None:
    """Authenticate a user by username and password."""
    db = get_db()
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def login(username: str, password: str) -> dict:
    """Login and return access token."""
    user = authenticate(username, password)
    if not user:
        raise ValueError("Invalid credentials")
    token = create_access_token({"sub": user.username})
    Session.create(user_id=user.id, token=token)
    return {"access_token": token, "token_type": "bearer"}
`,
    language: 'python',
    highlights: [{ startLine: 34, endLine: 40 }],
  },
  {
    id: 'models',
    filename: 'models.py',
    content: `"""Data models for RepoTalk."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    id: int
    username: str
    email: str
    hashed_password: str
    created_at: datetime

    @property
    def is_active(self) -> bool:
        return True


@dataclass
class Session:
    id: int
    user_id: int
    token: str
    created_at: datetime
    expires_at: datetime

    @classmethod
    def create(cls, user_id: int, token: str) -> "Session":
        return cls(
            id=0,
            user_id=user_id,
            token=token,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow(),
        )
`,
    language: 'python',
  },
];

export function SourceView() {
  const { theme } = useUIStore();
  const [tabs, setTabs] = useState<SourceTab[]>(sampleTabs);
  const [activeTab, setActiveTab] = useState(sampleTabs[0]?.id || '');

  const currentTab = tabs.find((t) => t.id === activeTab);

  const closeTab = (id: string) => {
    const newTabs = tabs.filter((t) => t.id !== id);
    setTabs(newTabs);
    if (activeTab === id && newTabs.length > 0) {
      setActiveTab(newTabs[0].id);
    }
  };

  const handleEditorMount = (editor: any, monaco: any) => {
    if (!currentTab?.highlights) return;
    const decorations = currentTab.highlights.map((h) => ({
      range: new monaco.Range(h.startLine, 1, h.endLine, 1),
      options: {
        isWholeLine: true,
        className: 'highlighted-line',
        glyphMarginClassName: 'highlighted-glyph',
      },
    }));
    editor.createDecorationsCollection(decorations);
  };

  if (tabs.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
        Click a reference in chat to view source code
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Tab bar */}
      <div className="flex items-center border-b border-border bg-muted/30 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 text-xs border-r border-border shrink-0 group',
              activeTab === tab.id
                ? 'bg-card text-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            )}
          >
            <span className="font-mono">{tab.filename}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                closeTab(tab.id);
              }}
              className="opacity-0 group-hover:opacity-100 hover:text-destructive transition-opacity"
            >
              <X className="w-3 h-3" />
            </button>
          </button>
        ))}
      </div>

      {/* Editor */}
      <div className="flex-1">
        {currentTab && (
          <Editor
            height="100%"
            language={currentTab.language}
            value={currentTab.content}
            theme={theme === 'dark' ? 'vs-dark' : 'vs'}
            onMount={handleEditorMount}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              fontSize: 13,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              padding: { top: 8 },
              renderLineHighlight: 'all',
              smoothScrolling: true,
            }}
          />
        )}
      </div>
    </div>
  );
}
