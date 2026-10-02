"use client";

import { useState } from "react";
import { ChevronDown, Crown, FlaskConical } from "lucide-react";
import { cn, formatNumber, formatSeconds } from "@/lib/utils";
import type { Experiment } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/empty-state";
import { MetricsCompareChart } from "@/components/charts/metrics-compare-chart";
import { FeatureImportanceChart } from "@/components/charts/feature-importance-chart";
import { ConfusionMatrixGrid } from "@/components/charts/confusion-matrix";

function HyperparameterChips({ params }: { params: Record<string, unknown> }) {
  const entries = Object.entries(params);
  if (entries.length === 0) {
    return <p className="text-sm text-zinc-500">Default hyperparameters.</p>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map(([key, value]) => (
        <span
          key={key}
          className="rounded-md border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[11px] text-zinc-300"
        >
          {key}=<span className="text-accent">{JSON.stringify(value)}</span>
        </span>
      ))}
    </div>
  );
}

export function ExperimentsTab({
  experiments,
  bestExperimentId,
}: {
  experiments: Experiment[];
  bestExperimentId: string | null;
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (experiments.length === 0) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="No experiments yet"
        description="Once the agent reaches the baseline stage, trained models will appear here ranked best-first."
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-10">#</TableHead>
          <TableHead>Model</TableHead>
          <TableHead>Stage</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Primary metric</TableHead>
          <TableHead className="text-right">Validation metrics</TableHead>
          <TableHead className="text-right">Train time</TableHead>
          <TableHead className="w-10" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {experiments.map((experiment, index) => {
          const isBest = experiment.id === bestExperimentId || (bestExperimentId === null && index === 0);
          const expanded = expandedId === experiment.id;
          const valMetrics = experiment.metrics.filter((m) => m.split === "validation");
          return [
            <TableRow
              key={experiment.id}
              onClick={() => setExpandedId(expanded ? null : experiment.id)}
              className={cn(
                "cursor-pointer",
                isBest && "bg-brand/[0.06] shadow-[inset_0_0_0_1px_rgba(139,92,246,0.35)]"
              )}
            >
              <TableCell className="text-zinc-500">{index + 1}</TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-zinc-100">{experiment.model_type}</span>
                  {isBest ? (
                    <Badge variant="default">
                      <Crown className="h-3 w-3" />
                      Best
                    </Badge>
                  ) : null}
                </div>
                <span className="text-xs text-zinc-500">{experiment.name}</span>
              </TableCell>
              <TableCell>
                <Badge variant={experiment.stage === "baseline" ? "secondary" : "info"}>
                  {experiment.stage}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge
                  variant={
                    experiment.status === "completed"
                      ? "success"
                      : experiment.status === "failed"
                        ? "destructive"
                        : experiment.status === "running"
                          ? "info"
                          : "secondary"
                  }
                >
                  {experiment.status}
                </Badge>
              </TableCell>
              <TableCell className="text-right">
                <span className="font-bold tabular-nums text-zinc-100">
                  {formatNumber(experiment.primary_metric_value)}
                </span>
                {experiment.primary_metric_name ? (
                  <span className="ml-1 text-[10px] uppercase text-zinc-500">
                    {experiment.primary_metric_name}
                  </span>
                ) : null}
              </TableCell>
              <TableCell className="text-right text-xs tabular-nums text-zinc-400">
                {valMetrics
                  .slice(0, 3)
                  .map((m) => `${m.name} ${formatNumber(m.value)}`)
                  .join(" · ") || "—"}
              </TableCell>
              <TableCell className="text-right tabular-nums text-zinc-400">
                {formatSeconds(experiment.train_seconds)}
              </TableCell>
              <TableCell>
                <ChevronDown
                  className={cn(
                    "h-4 w-4 text-zinc-500 transition-transform",
                    expanded && "rotate-180"
                  )}
                />
              </TableCell>
            </TableRow>,
            expanded ? (
              <TableRow key={`${experiment.id}-detail`} className="hover:bg-transparent">
                <TableCell colSpan={8} className="bg-white/[0.02] p-5">
                  {experiment.error ? (
                    <p className="mb-4 rounded-xl border border-red-400/20 bg-red-400/5 px-4 py-2 text-sm text-red-300">
                      {experiment.error}
                    </p>
                  ) : null}
                  <div className="grid gap-6 lg:grid-cols-2">
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                        Hyperparameters
                      </h4>
                      <HyperparameterChips params={experiment.hyperparameters} />
                      <h4 className="pt-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                        Train vs validation
                      </h4>
                      <MetricsCompareChart metrics={experiment.metrics} />
                    </div>
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                        Feature importance
                      </h4>
                      <FeatureImportanceChart data={experiment.feature_importance} limit={10} />
                      {experiment.confusion_matrix ? (
                        <>
                          <h4 className="pt-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                            Confusion matrix
                          </h4>
                          <ConfusionMatrixGrid matrix={experiment.confusion_matrix} />
                        </>
                      ) : null}
                    </div>
                  </div>
                </TableCell>
              </TableRow>
            ) : null,
          ];
        })}
      </TableBody>
    </Table>
  );
}
