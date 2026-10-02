import { Check, Loader2, X, Circle, SkipForward } from "lucide-react";
import { cn } from "@/lib/utils";
import { STAGE_LABELS, STAGE_ORDER, type RunStatus, type StageStatus } from "@/lib/types";
import { Progress } from "@/components/ui/progress";

function StageIcon({ status }: { status: StageStatus }) {
  switch (status) {
    case "completed":
      return <Check className="h-3.5 w-3.5" />;
    case "running":
      return <Loader2 className="h-3.5 w-3.5 animate-spin" />;
    case "failed":
      return <X className="h-3.5 w-3.5" />;
    case "skipped":
      return <SkipForward className="h-3.5 w-3.5" />;
    default:
      return <Circle className="h-3.5 w-3.5" />;
  }
}

const nodeStyles: Record<StageStatus, string> = {
  completed: "border-emerald-400/40 bg-emerald-400/15 text-emerald-300",
  running: "border-cyan-400/50 bg-cyan-400/15 text-cyan-300 animate-pulse-glow",
  failed: "border-red-400/40 bg-red-400/15 text-red-300",
  skipped: "border-white/10 bg-white/5 text-zinc-500",
  pending: "border-white/10 bg-white/5 text-zinc-600",
};

export function PipelineTimeline({ status }: { status: RunStatus | undefined }) {
  const stages = STAGE_ORDER.map((name) => {
    const found = status?.stages.find((s) => s.name === name);
    return { name, status: found?.status ?? ("pending" as StageStatus) };
  });
  const progress = status?.progress ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-xs text-zinc-500">
        <span className="font-medium uppercase tracking-wider">Pipeline</span>
        <span className="tabular-nums">{Math.round(progress)}%</span>
      </div>
      <Progress value={progress} />

      {/* Horizontal (md+) */}
      <ol className="hidden items-start md:flex">
        {stages.map((stage, index) => (
          <li key={stage.name} className="relative flex flex-1 flex-col items-center gap-2">
            {index > 0 ? (
              <div
                className={cn(
                  "absolute right-1/2 top-4 h-px w-full -translate-y-1/2",
                  stage.status === "completed" || stage.status === "running"
                    ? "bg-gradient-to-r from-emerald-400/40 to-current"
                    : "bg-white/10"
                )}
              />
            ) : null}
            <div
              className={cn(
                "relative z-10 flex h-8 w-8 items-center justify-center rounded-full border",
                nodeStyles[stage.status]
              )}
            >
              <StageIcon status={stage.status} />
            </div>
            <span
              className={cn(
                "text-[11px] font-medium",
                stage.status === "pending" ? "text-zinc-600" : "text-zinc-300"
              )}
            >
              {STAGE_LABELS[stage.name] ?? stage.name}
            </span>
          </li>
        ))}
      </ol>

      {/* Vertical (mobile) */}
      <ol className="flex flex-col gap-1 md:hidden">
        {stages.map((stage, index) => (
          <li key={stage.name} className="flex items-center gap-3">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full border",
                  nodeStyles[stage.status]
                )}
              >
                <StageIcon status={stage.status} />
              </div>
              {index < stages.length - 1 ? <div className="h-3 w-px bg-white/10" /> : null}
            </div>
            <span
              className={cn(
                "text-sm",
                stage.status === "pending" ? "text-zinc-600" : "text-zinc-200"
              )}
            >
              {STAGE_LABELS[stage.name] ?? stage.name}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
