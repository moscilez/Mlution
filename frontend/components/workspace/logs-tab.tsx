"use client";
import { useI18n } from "@/lib/i18n";
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
  const { t } = useI18n();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events.length]);

  if (events.length === 0) {
    return (
      <EmptyState
        icon={ScrollText}
        title={t("No log entries yet")}
        description={t(
          "Agent events will stream here in real time once a run is in progress.",
        )}
      />
    );
  }

  return (
    <div
      ref={scrollRef}
      className="max-h-[520px] space-y-1 overflow-y-auto rounded-xl border border-zinc-200 bg-zinc-50 p-3 font-mono text-xs"
    >
      {events.map((event) => (
        <div
          key={event.id}
          className="flex items-start gap-3 rounded-md px-2 py-1 hover:bg-zinc-100"
        >
          <span className="shrink-0 tabular-nums text-zinc-500">
            {formatTime(event.ts)}
          </span>
          <span
            className={cn(
              "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
              levelDot[event.level],
            )}
          />
          <span className="w-24 shrink-0 truncate text-zinc-500">
            {t(event.agent)}
          </span>
          <span className="w-28 shrink-0 truncate text-zinc-500">
            {t(event.stage)}
          </span>
          <span className="text-zinc-700">{t(event.message)}</span>
        </div>
      ))}
    </div>
  );
}
