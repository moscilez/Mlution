"use client";
import { useI18n } from "@/lib/i18n";
import { Check, GitBranch, X } from "lucide-react";
import type { ImprovementStep } from "@/lib/types";
import { formatNumber } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export function ImprovementsList({ steps }: { steps: ImprovementStep[] }) {
  const { t } = useI18n();
  if (steps.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-zinc-500">
        {t("No improvement steps were applied in this run.")}
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
            className="rounded-2xl border border-zinc-200 bg-zinc-100 p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-brand" />
                <p className="text-sm font-medium text-zinc-900">
                  {t(step.hypothesis)}
                </p>
              </div>
              <Badge
                variant={accepted ? "default" : "secondary"}
                className={
                  accepted
                    ? "bg-emerald-500/15 text-emerald-700 border border-emerald-400/30"
                    : "bg-zinc-500/15 text-zinc-700 border border-zinc-400/30"
                }
              >
                {accepted ? (
                  <span className="flex items-center gap-1">
                    <Check className="h-3 w-3" />
                    {t("accepted")}
                  </span>
                ) : (
                  <span className="flex items-center gap-1">
                    <X className="h-3 w-3" />
                    {t("rejected")}
                  </span>
                )}
              </Badge>
            </div>
            <p className="mt-2 text-sm text-zinc-600">{t(step.reason)}</p>
            <p className="mt-1 text-sm text-zinc-700">
              <span className="text-zinc-500">{t("Action:")}</span>
              {t(step.action)}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-3 font-mono text-xs">
              {Object.keys(step.after).map((metric) => (
                <span
                  key={metric}
                  className="rounded-lg border border-zinc-200 bg-zinc-100 px-2.5 py-1 text-zinc-700"
                >
                  {t(metric)}
                  {t(":")}
                  {t(" ")}
                  <span className="text-zinc-500">
                    {t(formatNumber(step.before[metric]))}
                  </span>
                  {t(" → ")}
                  <span
                    className={accepted ? "text-emerald-700" : "text-zinc-800"}
                  >
                    {t(formatNumber(step.after[metric]))}
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
