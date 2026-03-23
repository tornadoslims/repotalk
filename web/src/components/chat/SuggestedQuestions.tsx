import { useChatStore } from '@/stores/chatStore';
import { Sparkles } from 'lucide-react';

interface SuggestedQuestionsProps {
  onSelect?: (question: string) => void;
}

export function SuggestedQuestions({ onSelect }: SuggestedQuestionsProps) {
  const { suggestedQuestions } = useChatStore();

  if (suggestedQuestions.length === 0) return null;

  return (
    <div className="px-4 pb-2">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1.5">
        <Sparkles className="w-3 h-3" />
        Follow-up questions
      </div>
      <div className="flex flex-wrap gap-1.5">
        {suggestedQuestions.map((q, i) => (
          <button
            key={i}
            onClick={() => onSelect?.(q)}
            className="text-xs px-3 py-1.5 rounded-full border border-border hover:bg-muted hover:border-primary/30 transition-colors text-muted-foreground hover:text-foreground"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
