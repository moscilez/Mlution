"use client";

import { useEffect, useRef } from "react";
import { ScrollText } from "lucide-react";
import { cn, formatTime } from "@/lib/utils";
import type { AgentEvent, EventLevel } from "@/lib/types";
import { EmptyState } from "@/components/empty-state";

const levelDot: Record<EventLevel, string> = {
  info: "bg-zinc-400",
  success: "bg-emerald-400",
  warning: "bg-amber-400",
  error: "bg-red-400",
};

export function LogsTab({ events }: { events: AgentEvent[] }) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events.length]);

  if (events.length === 0) {
    return (
      <EmptyState
        icon={ScrollText}
        title="No log entries yet"
        description="Agent events will stream here in real time once a run is in progress."
      />
    );
  }

  return (
    <div
      ref={scrollRef}
      className="max-h-[520px] space-y-1 overflow-y-auto rounded-xl border border-white/10 bg-black/30 p-3 font-mono text-xs"
    >
      {events.map((event) => (
        <div key={event.id} className="flex items-start gap-3 rounded-md px-2 py-1 hover:bg-white/[0.03]">
          <span className="shrink-0 tabular-nums text-zinc-600">{formatTime(event.ts)}</span>
          <span className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", levelDot[event.level])} />
          <span className="w-24 shrink-0 truncate text-zinc-500">{event.agent}</span>
          <span className="w-28 shrink-0 truncate text-zinc-600">{event.stage}</span>
          <span className="text-zinc-300">{event.message}</span>
        </div>
      ))}
    </div>
  );
}
