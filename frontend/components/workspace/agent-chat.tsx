"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Bot, Loader2, SendHorizonal, User } from "lucide-react";
import { sendChat } from "@/lib/api";
import { cn, formatTime } from "@/lib/utils";
import type { AgentEvent, EventLevel } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const levelDot: Record<EventLevel, string> = {
  info: "bg-zinc-400",
  success: "bg-emerald-400",
  warning: "bg-amber-400",
  error: "bg-red-400",
};

const levelText: Record<EventLevel, string> = {
  info: "text-zinc-300",
  success: "text-emerald-200",
  warning: "text-amber-200",
  error: "text-red-200",
};

interface ChatTurn {
  role: "user" | "agent";
  text: string;
  ts: string;
}

interface EventGroup {
  agent: string;
  events: AgentEvent[];
}

export function AgentChat({
  projectId,
  events,
  className,
}: {
  projectId: string;
  events: AgentEvent[];
  className?: string;
}) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const groups = useMemo<EventGroup[]>(() => {
    const out: EventGroup[] = [];
    for (const event of events) {
      const last = out[out.length - 1];
      if (last && last.agent === event.agent) {
        last.events.push(event);
      } else {
        out.push({ agent: event.agent, events: [event] });
      }
    }
    return out;
  }, [events]);

  const chatMutation = useMutation({
    mutationFn: (message: string) => sendChat(projectId, message),
    onSuccess: (reply) => {
      setTurns((t) => [...t, { role: "agent", text: reply.reply, ts: reply.ts }]);
    },
    onError: (error) => {
      setTurns((t) => [
        ...t,
        {
          role: "agent",
          text: `I could not answer that right now: ${error instanceof Error ? error.message : "unknown error"}`,
          ts: new Date().toISOString(),
        },
      ]);
    },
  });

  const itemCount = events.length + turns.length;
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [itemCount]);

  const submit = () => {
    const message = draft.trim();
    if (!message || chatMutation.isPending) return;
    setTurns((t) => [...t, { role: "user", text: message, ts: new Date().toISOString() }]);
    setDraft("");
    chatMutation.mutate(message);
  };

  return (
    <div className={cn("flex min-h-0 flex-col", className)}>
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
        <Bot className="h-4 w-4 text-brand" />
        <p className="text-sm font-semibold text-zinc-100">Agent activity</p>
        <span className="ml-auto text-xs text-zinc-500">{events.length} events</span>
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {groups.length === 0 && turns.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <Bot className="h-8 w-8 text-zinc-600" />
            <p className="text-sm text-zinc-500">
              The agent has not said anything yet. Start a run to see it think.
            </p>
          </div>
        ) : null}

        {groups.map((group, gi) => (
          <div key={gi} className="flex gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-brand/30 bg-brand/15 text-xs font-bold text-violet-200">
              {group.agent.slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1 space-y-1.5">
              <div className="flex items-baseline gap-2">
                <span className="text-xs font-semibold text-zinc-200">{group.agent}</span>
                <span className="text-[10px] text-zinc-600">
                  {formatTime(group.events[0].ts)}
                </span>
              </div>
              {group.events.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-2 rounded-xl rounded-tl-sm border border-white/5 bg-white/[0.03] px-3 py-2"
                >
                  <span
                    className={cn("mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full", levelDot[event.level])}
                  />
                  <div className="min-w-0">
                    <p className={cn("text-sm leading-relaxed", levelText[event.level])}>
                      {event.message}
                    </p>
                    <p className="mt-0.5 text-[10px] text-zinc-600">
                      {event.stage} · {formatTime(event.ts)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {turns.map((turn, i) =>
          turn.role === "user" ? (
            <div key={`u-${i}`} className="flex justify-end gap-3">
              <div className="max-w-[85%] rounded-xl rounded-tr-sm border border-brand/30 bg-brand/20 px-3 py-2">
                <p className="text-sm text-violet-100">{turn.text}</p>
                <p className="mt-0.5 text-right text-[10px] text-violet-300/60">
                  {formatTime(turn.ts)}
                </p>
              </div>
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/15 bg-white/10 text-zinc-300">
                <User className="h-4 w-4" />
              </div>
            </div>
          ) : (
            <div key={`a-${i}`} className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-brand/30 bg-brand/15 text-xs font-bold text-violet-200">
                M
              </div>
              <div className="max-w-[85%] rounded-xl rounded-tl-sm border border-white/5 bg-white/[0.03] px-3 py-2">
                <p className="text-sm text-zinc-200">{turn.text}</p>
                <p className="mt-0.5 text-[10px] text-zinc-600">{formatTime(turn.ts)}</p>
              </div>
            </div>
          )
        )}

        {chatMutation.isPending ? (
          <div className="flex gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-brand/30 bg-brand/15 text-xs font-bold text-violet-200">
              M
            </div>
            <div className="flex items-center gap-2 rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2 text-sm text-zinc-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Thinking…
            </div>
          </div>
        ) : null}
      </div>

      <div className="border-t border-white/10 p-3">
        <form
          className="flex items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask the agent about this project…"
            className="h-9"
          />
          <Button
            type="submit"
            size="icon"
            className="h-9 w-9 shrink-0"
            disabled={!draft.trim() || chatMutation.isPending}
            aria-label="Send message"
          >
            <SendHorizonal className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
