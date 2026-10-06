"use client";
import { useState } from "react";
import { useI18n } from "@/lib/i18n";
import { Check, Loader2, X, Circle, SkipForward } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  STAGE_LABELS,
  STAGE_ORDER,
  type RunStatus,
  type StageStatus,
} from "@/lib/types";
import { Progress } from "@/components/ui/progress";

const descriptions = {
  ru: [
    "Проверяем структуру данных, пропуски, дубликаты и возможную утечку целевой информации.",
    "Определяем тип задачи и выбираем метрики под вашу цель.",
    "Обучаем базовую модель и кандидатов для сравнения.",
    "Сравниваем качество на обучении и валидации, изучаем ошибки.",
    "Проверяем риски, дисбаланс классов и признаки переобучения.",
    "Проверяем гипотезы и сохраняем изменения, которые улучшают метрику.",
    "Собираем лучшую модель, отчёт и Python-код для предсказаний.",
  ],
  en: [
    "Check data structure, missing values, duplicates and potential target leakage.",
    "Identify the task type and choose metrics for your objective.",
    "Train a baseline and candidate models for comparison.",
    "Compare training and validation quality and explore errors.",
    "Review risks, class imbalance and signs of overfitting.",
    "Test hypotheses and retain changes that improve the metric.",
    "Package the best model, report and Python prediction code.",
  ],
};
const labels: Record<StageStatus, string> = {
  pending: "Pending",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  skipped: "Skipped",
};
const styles: Record<StageStatus, string> = {
  completed: "border-emerald-200 bg-emerald-50 text-emerald-700",
  running: "border-blue-300 bg-blue-50 text-blue-700 animate-pulse-glow",
  failed: "border-red-200 bg-red-50 text-red-700",
  skipped: "border-zinc-200 bg-zinc-50 text-zinc-500",
  pending: "border-zinc-200 bg-white text-zinc-500",
};

function StageIcon({ status }: { status: StageStatus }) {
  const Icon =
    status === "completed"
      ? Check
      : status === "running"
        ? Loader2
        : status === "failed"
          ? X
          : status === "skipped"
            ? SkipForward
            : Circle;
  return (
    <Icon
      size={14}
      className={status === "running" ? "animate-spin" : ""}
      aria-hidden="true"
    />
  );
}

export function PipelineTimeline({
  status,
}: {
  status: RunStatus | undefined;
}) {
  const { t, locale } = useI18n();
  const [selected, setSelected] = useState<string | null>(null);
  const stages = STAGE_ORDER.map((name) => ({
    name,
    status:
      status?.stages.find((s) => s.name === name)?.status ??
      ("pending" as StageStatus),
  }));
  const current =
    selected ??
    (status?.status === "completed"
      ? "finalize"
      : (status?.stage ?? "analyze"));
  const index = Math.max(
    0,
    stages.findIndex((stage) => stage.name === current),
  );
  const stage = stages[index];
  // The API uses a fraction in [0, 1]; the progress component expects percent.
  const progress = Math.min(100, Math.max(0, (status?.progress ?? 0) * 100));
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between text-xs text-zinc-500">
        <span className="font-medium">{t("Pipeline")}</span>
        <span className="tabular-nums">{Math.round(progress)}%</span>
      </div>
      <Progress value={progress} aria-label={t("Pipeline")} />
      <ol
        className="grid grid-cols-4 gap-2 md:grid-cols-7"
        aria-label={t("Pipeline")}
      >
        {stages.map((item, i) => (
          <li key={item.name} className="min-w-0">
            <button
              type="button"
              aria-pressed={stage.name === item.name}
              aria-label={`${t(STAGE_LABELS[item.name])}: ${t(labels[item.status])}`}
              onClick={() => setSelected(item.name)}
              className={cn(
                "flex w-full flex-col items-start gap-2 rounded-xl border p-3 text-left transition-colors hover:border-blue-300",
                stage.name === item.name
                  ? "border-blue-200 bg-blue-50/50"
                  : "border-transparent bg-zinc-50",
              )}
            >
              <div className="flex w-full items-center justify-between gap-1">
                <span
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-full border",
                    styles[item.status],
                  )}
                >
                  <StageIcon status={item.status} />
                </span>
                <span className="text-[9px] text-zinc-400">0{i + 1}</span>
              </div>
              <span className="text-[10px] font-medium text-zinc-700 sm:text-xs">
                {t(STAGE_LABELS[item.name])}
              </span>
            </button>
          </li>
        ))}
      </ol>
      <div
        className="flex flex-col gap-2 border-t border-zinc-100 pt-4 sm:flex-row sm:items-start sm:gap-6"
        aria-live="polite"
      >
        <div className="flex shrink-0 items-center gap-2">
          <span className="text-xs font-semibold text-zinc-900">
            {t(STAGE_LABELS[stage.name])}
          </span>
          <span
            className={cn(
              "rounded-full border px-2 py-0.5 text-[10px]",
              styles[stage.status],
            )}
          >
            {t(labels[stage.status])}
          </span>
        </div>
        <p className="text-xs leading-relaxed text-zinc-600">
          {descriptions[locale][index]}
        </p>
      </div>
    </div>
  );
}
