"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { eventsStreamUrl } from "./api";
import type { AgentEvent } from "./types";

export interface LiveProject {
  /** true when SSE failed and queries should poll instead */
  fallback: boolean;
  /** pass to useQuery refetchInterval */
  refetchInterval: number | false;
}

const LIVE_KEYS = ["status", "events", "experiments", "project"] as const;

export function useLiveProject(projectId: string, enabled = true): LiveProject {
  const queryClient = useQueryClient();
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    let closed = false;
    const source = new EventSource(eventsStreamUrl(projectId), {
      withCredentials: true,
    });
    source.onopen = () => setFallback(false);
    source.addEventListener("close", () => {
      closed = true;
      source.close();
    });

    source.onmessage = (msg: MessageEvent<string>) => {
      try {
        const event = JSON.parse(msg.data) as AgentEvent;
        queryClient.setQueryData<AgentEvent[]>(["events", projectId], (old) => {
          if (!old) return old;
          if (old.some((e) => e.id === event.id)) return old;
          return [...old, event];
        });
      } catch {
        // ignore malformed event payloads
      }
      for (const key of LIVE_KEYS) {
        if (key === "events") continue;
        void queryClient.invalidateQueries({ queryKey: [key, projectId] });
      }
    };

    source.onerror = () => {
      if (closed) return;
      setFallback(true);
      // EventSource reconnects with Last-Event-ID; polling covers the outage.
    };

    return () => {
      closed = true;
      source.close();
    };
  }, [projectId, enabled, queryClient]);

  return { fallback, refetchInterval: enabled ? 2500 : false };
}
