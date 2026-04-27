/** SSE hook — subscribe to Server-Sent Events for live job progress. */

import { useEffect, useRef, useCallback, useState } from 'react';

export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

export function useSSE(
  jobId: string | null,
  onEvent: (evt: SSEEvent) => void,
) {
  const sourceRef = useRef<EventSource | null>(null);
  const [connected, setConnected] = useState(false);

  const connect = useCallback(() => {
    if (!jobId) return;

    const url = `/api/jobs/${jobId}/events`;
    const source = new EventSource(url);
    sourceRef.current = source;

    source.onopen = () => setConnected(true);

    // Listen for all event types
    const eventTypes = [
      'job_started', 'entry_started', 'entry_completed',
      'entry_failed', 'job_completed', 'job_cancelled', 'error',
    ];

    eventTypes.forEach((type) => {
      source.addEventListener(type, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data);
          onEvent({ event: type, data });
        } catch {
          onEvent({ event: type, data: { raw: e.data } });
        }
      });
    });

    source.onerror = () => {
      setConnected(false);
      source.close();
      // Reconnect after 3 seconds
      setTimeout(() => connect(), 3000);
    };
  }, [jobId, onEvent]);

  useEffect(() => {
    connect();
    return () => {
      if (sourceRef.current) {
        sourceRef.current.close();
        sourceRef.current = null;
      }
    };
  }, [connect]);

  const disconnect = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
      setConnected(false);
    }
  }, []);

  return { connected, disconnect };
}
