"use client";
import { useI18n } from "@/lib/i18n";
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
  const { t } = useI18n();
  const entries = Object.entries(params);
  if (entries.length === 0) {
    return (
      <p className="text-sm text-zinc-500">{t("Default hyperparameters.")}</p>
    );
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {entries.map(([key, value]) => (
        <span
          key={key}
          className="rounded-md border border-zinc-200 bg-zinc-100 px-2 py-0.5 font-mono text-[11px] text-zinc-700"
        >
          {t(key)}
          {t("=")}
          <span className="text-accent">{t(JSON.stringify(value))}</span>
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
  const { t } = useI18n();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("rank");
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  const visible = experiments.filter(
    (e) => filter === "all" || e.status === filter,
  );
  if (sort === "duration")
    visible.sort(
      (a, b) => (a.train_seconds ?? Infinity) - (b.train_seconds ?? Infinity),
    );
  if (sort === "model")
    visible.sort((a, b) => a.model_type.localeCompare(b.model_type));
  const left = experiments.find((e) => e.id === first);
  const right = experiments.find((e) => e.id === second);

  if (experiments.length === 0) {
    return (
      <EmptyState
        icon={FlaskConical}
        title={t("No experiments yet")}
        description={t(
          "Once the agent reaches the baseline stage, trained models will appear here ranked best-first.",
        )}
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 text-sm">
        <label>
          {t("Status")}
          {t(" ")}
          <select
            aria-label={t("Filter experiment status")}
            className="ml-2 rounded-lg border border-zinc-200 bg-card p-2"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">{t("All")}</option>
            <option value="completed">{t("Completed")}</option>
            <option value="running">{t("Running")}</option>
            <option value="failed">{t("Failed")}</option>
          </select>
        </label>
        <label>
          {t("Sort")}
          {t(" ")}
          <select
            aria-label={t("Sort experiments")}
            className="ml-2 rounded-lg border border-zinc-200 bg-card p-2"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="rank">{t("Metric rank")}</option>
            <option value="duration">{t("Training time")}</option>
            <option value="model">{t("Model name")}</option>
          </select>
        </label>
        {[
          { label: "Compare first", value: first, set: setFirst },
          { label: "Compare second", value: second, set: setSecond },
        ].map(({ label, value, set }) => (
          <label key={label}>
            {t(label)}
            <select
              aria-label={label}
              className="ml-2 max-w-48 rounded-lg border border-zinc-200 bg-card p-2"
              value={value}
              onChange={(e) => set(e.target.value)}
            >
              <option value="">{t("Choose model")}</option>
              {experiments
                .filter((e) => e.status === "completed")
                .map((e) => (
                  <option key={e.id} value={e.id}>
                    {t(e.name)}
                    {t("·")}
                    {e.id.slice(0, 6)}
                  </option>
                ))}
            </select>
          </label>
        ))}
      </div>
      {left && right && first !== second && (
        <div className="overflow-auto rounded-xl border border-cyan-400/20 p-4">
          <p className="mb-3 text-sm text-blue-700">
            {t("Validation metrics:")}
            {t(left.name)}
            {t("/")}
            {t(right.name)}
          </p>
          {left.metrics
            .filter((m) => m.split === "validation")
            .map((m) => (
              <div key={m.name} className="grid grid-cols-3 gap-4 py-1 text-xs">
                <span>{t(m.name)}</span>
                <span>{t(formatNumber(m.value))}</span>
                <span>
                  {formatNumber(
                    right.metrics.find(
                      (r) => r.name === m.name && r.split === "validation",
                    )?.value ?? null,
                  )}
                </span>
              </div>
            ))}
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10">{t("#")}</TableHead>
            <TableHead>{t("Model")}</TableHead>
            <TableHead>{t("Stage")}</TableHead>
            <TableHead>{t("Status")}</TableHead>
            <TableHead className="text-right">{t("Primary metric")}</TableHead>
            <TableHead className="text-right">
              {t("Validation metrics")}
            </TableHead>
            <TableHead className="text-right">{t("Train time")}</TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {visible.map((experiment, index) => {
            const isBest =
              experiment.id === bestExperimentId ||
              (bestExperimentId === null && index === 0);
            const expanded = expandedId === experiment.id;
            const valMetrics = experiment.metrics.filter(
              (m) => m.split === "validation",
            );
            return [
              <TableRow
                key={experiment.id}
                onClick={() => setExpandedId(expanded ? null : experiment.id)}
                className={cn(
                  "cursor-pointer",
                  isBest &&
                    "bg-brand/[0.06] shadow-[inset_0_0_0_1px_rgba(0,113,227,0.25)]",
                )}
              >
                <TableCell className="text-zinc-500">{t(index + 1)}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-zinc-900">
                      {t(experiment.model_type)}
                    </span>
                    {isBest ? (
                      <Badge variant="default">
                        <Crown className="h-3 w-3" />
                        {t("Best")}
                      </Badge>
                    ) : null}
                  </div>
                  <span className="text-xs text-zinc-500">
                    {t(experiment.name)}
                  </span>
                </TableCell>
                <TableCell>
                  <Badge
                    variant={
                      experiment.stage === "baseline" ? "secondary" : "info"
                    }
                  >
                    {t(experiment.stage)}
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
                    {t(experiment.status)}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <span className="font-bold tabular-nums text-zinc-900">
                    {t(formatNumber(experiment.primary_metric_value))}
                  </span>
                  {experiment.primary_metric_name ? (
                    <span className="ml-1 text-[10px] uppercase text-zinc-500">
                      {t(experiment.primary_metric_name)}
                    </span>
                  ) : null}
                </TableCell>
                <TableCell className="text-right text-xs tabular-nums text-zinc-600">
                  {valMetrics
                    .slice(0, 3)
                    .map((m) => `${m.name} ${formatNumber(m.value)}`)
                    .join(" · ") || "—"}
                </TableCell>
                <TableCell className="text-right tabular-nums text-zinc-600">
                  {t(formatSeconds(experiment.train_seconds))}
                </TableCell>
                <TableCell>
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 text-zinc-500 transition-transform",
                      expanded && "rotate-180",
                    )}
                  />
                </TableCell>
              </TableRow>,
              expanded ? (
                <TableRow
                  key={`${experiment.id}-detail`}
                  className="hover:bg-transparent"
                >
                  <TableCell colSpan={8} className="bg-zinc-100 p-5">
                    {experiment.error ? (
                      <p className="mb-4 rounded-xl border border-red-400/20 bg-red-400/5 px-4 py-2 text-sm text-red-700">
                        {experiment.error}
                      </p>
                    ) : null}
                    <div className="grid gap-6 lg:grid-cols-2">
                      <div className="space-y-2">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                          {t("Hyperparameters")}
                        </h4>
                        <HyperparameterChips
                          params={experiment.hyperparameters}
                        />
                        <h4 className="pt-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                          {t("Train vs validation")}
                        </h4>
                        <MetricsCompareChart metrics={experiment.metrics} />
                      </div>
                      <div className="space-y-2">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                          {t("Feature importance")}
                        </h4>
                        <FeatureImportanceChart
                          data={experiment.feature_importance}
                          limit={10}
                        />
                        {experiment.confusion_matrix ? (
                          <>
                            <h4 className="pt-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                              {t("Confusion matrix")}
                            </h4>
                            <ConfusionMatrixGrid
                              matrix={experiment.confusion_matrix}
                            />
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
    </div>
  );
}
