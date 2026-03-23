import { useRef, useCallback } from 'react';
import type { SSECallbacks } from '@/api/sse';
import { sendMessage } from '@/api/sse';

export function useSSE() {
  const controllerRef = useRef<AbortController | null>(null);

  const send = useCallback(
    (conversationId: string, content: string, callbacks: SSECallbacks, options?: { pinned_files?: string[]; scope?: string }) => {
      // Abort previous stream
      controllerRef.current?.abort();
      controllerRef.current = sendMessage(conversationId, content, callbacks, options);
    },
    []
  );

  const abort = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
  }, []);

  return { send, abort };
}
