import type { SSEEvent } from './types';

export interface SSECallbacks {
  onToken?: (content: string) => void;
  onReference?: (file: string, line?: number) => void;
  onGraphHighlight?: (nodes: string[]) => void;
  onDone?: (cost?: number) => void;
  onSuggestions?: (questions: string[]) => void;
  onError?: (message: string) => void;
}

export function sendMessage(
  conversationId: string,
  content: string,
  callbacks: SSECallbacks,
  options?: { pinned_files?: string[]; scope?: string }
): AbortController {
  const controller = new AbortController();

  const body = JSON.stringify({
    content,
    pinned_files: options?.pinned_files,
    scope: options?.scope,
  });

  fetch(`/api/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body,
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const text = await res.text();
        callbacks.onError?.(text || res.statusText);
        return;
      }
      const reader = res.body?.getReader();
      if (!reader) {
        callbacks.onError?.('No response body');
        return;
      }
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE events (separated by double newline)
        const events = buffer.split('\n\n');
        buffer = events.pop() || ''; // Keep incomplete event in buffer

        for (const eventBlock of events) {
          if (!eventBlock.trim()) continue;

          let eventType = '';
          let eventData = '';

          for (const line of eventBlock.split('\n')) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              eventData = line.slice(6);
            }
          }

          if (!eventData) continue;
          if (eventData === '[DONE]') {
            callbacks.onDone?.();
            return;
          }

          try {
            const parsed = JSON.parse(eventData);
            const type = eventType || parsed.type || '';

            // Dispatch based on event type
            if (type === 'token') {
              callbacks.onToken?.(parsed.content || '');
            } else if (type === 'reference') {
              callbacks.onReference?.(parsed.source || parsed.file || '', parsed.line);
            } else if (type === 'graph_highlight') {
              callbacks.onGraphHighlight?.(parsed.nodes || []);
            } else if (type === 'done') {
              callbacks.onDone?.(parsed.cost);
              return;
            } else if (type === 'suggestions') {
              callbacks.onSuggestions?.(parsed.suggestions || parsed.questions || []);
            } else if (type === 'error') {
              callbacks.onError?.(parsed.message || 'Unknown error');
            }
            // context_used — skip silently
          } catch {
            // Non-JSON data in a token event
            if (eventType === 'token' && eventData) {
              callbacks.onToken?.(eventData);
            }
          }
        }
      }

      callbacks.onDone?.();
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        callbacks.onError?.(err.message);
      }
    });

  return controller;
}
