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
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6).trim();
          if (data === '[DONE]') {
            callbacks.onDone?.();
            return;
          }
          try {
            const event: SSEEvent = JSON.parse(data);
            switch (event.type) {
              case 'token':
                callbacks.onToken?.(event.content || '');
                break;
              case 'reference':
                callbacks.onReference?.(event.file || '', event.line);
                break;
              case 'graph_highlight':
                callbacks.onGraphHighlight?.(event.nodes || []);
                break;
              case 'done':
                callbacks.onDone?.(event.cost);
                break;
              case 'suggestions':
                callbacks.onSuggestions?.(event.questions || []);
                break;
              case 'error':
                callbacks.onError?.(event.message || 'Unknown error');
                break;
            }
          } catch {
            // skip malformed JSON
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        callbacks.onError?.(err.message);
      }
    });

  return controller;
}
