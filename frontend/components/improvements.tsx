import { Check, GitBranch, X } from "lucide-react";
import type { ImprovementStep } from "@/lib/types";
import { formatNumber } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export function ImprovementsList({ steps }: { steps: ImprovementStep[] }) {
  if (steps.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-zinc-500">
        No improvement steps were applied in this run.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      {steps.map((step, i) => {
        const accepted = step.decision === "accept_improvement";
        return (
          <div
            key={i}
            className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-brand" />
                <p className="text-sm font-medium text-zinc-100">{step.hypothesis}</p>
              </div>
              <Badge
                variant={accepted ? "default" : "secondary"}
                className={
                  accepted
                    ? "bg-emerald-500/15 text-emerald-300 border border-emerald-400/30"
                    : "bg-zinc-500/15 text-zinc-300 border border-zinc-400/30"
                }
              >
                {accepted ? (
                  <span className="flex items-center gap-1"><Check className="h-3 w-3" /> accepted</span>
                ) : (
                  <span className="flex items-center gap-1"><X className="h-3 w-3" /> rejected</span>
                )}
              </Badge>
            </div>
            <p className="mt-2 text-sm text-zinc-400">{step.reason}</p>
            <p className="mt-1 text-sm text-zinc-300">
              <span className="text-zinc-500">Action: </span>
              {step.action}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-3 font-mono text-xs">
              {Object.keys(step.after).map((metric) => (
                <span
                  key={metric}
                  className="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-zinc-300"
                >
                  {metric}:{" "}
                  <span className="text-zinc-500">{formatNumber(step.before[metric])}</span>
                  {" → "}
                  <span className={accepted ? "text-emerald-300" : "text-zinc-200"}>
                    {formatNumber(step.after[metric])}
                  </span>
                </span>
              ))}
            </div>
            {step.details ? (
              <p className="mt-2 text-xs text-zinc-500">{step.details}</p>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
