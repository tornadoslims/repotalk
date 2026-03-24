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

      let currentEventType = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          // Track SSE event type
          if (line.startsWith('event: ')) {
            currentEventType = line.slice(7).trim();
            continue;
          }
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6).trim();
          if (data === '[DONE]') {
            callbacks.onDone?.();
            return;
          }
          try {
            const parsed = JSON.parse(data);
            // Use the SSE event type if the data doesn't have a 'type' matching our dispatch types
            const event: SSEEvent = {
              ...parsed,
              type: _normalizeEventType(parsed.type, currentEventType),
            };
            _dispatchEvent(event, callbacks);
          } catch {
            // If it's plain text (token streaming), treat as token
            if (data && currentEventType === 'token') {
              callbacks.onToken?.(data);
            }
          }
          currentEventType = '';
        }
      }

      // If stream ends without explicit done, signal completion
      callbacks.onDone?.();
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        callbacks.onError?.(err.message);
      }
    });

  return controller;
}

/** Map backend event/type names to our SSEEvent types */
function _normalizeEventType(dataType: string | undefined, sseEventType: string): SSEEvent['type'] {
  // Direct matches
  const t = dataType || sseEventType;
  const map: Record<string, SSEEvent['type']> = {
    token: 'token',
    reference: 'reference',
    file: 'reference',           // backend sends type:"file" for references
    directory: 'reference',
    graph_highlight: 'graph_highlight',
    done: 'done',
    suggestions: 'suggestions',
    error: 'error',
    context_used: 'context_used',
  };
  return map[t] || (sseEventType ? (map[sseEventType] || 'token') : 'token');
}

function _dispatchEvent(event: SSEEvent, callbacks: SSECallbacks) {
  switch (event.type) {
    case 'token':
      callbacks.onToken?.(event.content || '');
      break;
    case 'reference':
      callbacks.onReference?.(event.source || event.file || '', event.line);
      break;
    case 'graph_highlight':
      callbacks.onGraphHighlight?.(event.nodes || []);
      break;
    case 'done':
      callbacks.onDone?.(event.cost);
      break;
    case 'suggestions':
      callbacks.onSuggestions?.(event.suggestions || event.questions || []);
      break;
    case 'error':
      callbacks.onError?.(event.message || 'Unknown error');
      break;
    case 'context_used':
      // informational, no callback needed
      break;
  }
}
