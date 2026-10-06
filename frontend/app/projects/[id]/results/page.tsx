"use client";
import { useI18n } from "@/lib/i18n";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download, FileCode, Play, Trophy } from "lucide-react";
import {
  codeDownloadUrl,
  getExperiments,
  getProject,
  getReport,
  modelDownloadUrl,
} from "@/lib/api";
import { formatNumber, formatSeconds } from "@/lib/utils";
import { TASK_TYPE_LABELS } from "@/lib/types";
import { SiteHeader } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { ImprovementsList } from "@/components/improvements";
import { LeaderboardChart } from "@/components/charts/leaderboard-chart";
import { ConfusionMatrixGrid } from "@/components/charts/confusion-matrix";
import { FeatureImportanceChart } from "@/components/charts/feature-importance-chart";

export default function ResultsPage() {
  const { t } = useI18n();
  const projectId = useParams<{ id: string }>().id;

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });
  const experimentsQuery = useQuery({
    queryKey: ["experiments", projectId],
    queryFn: () => getExperiments(projectId),
  });
  const reportQuery = useQuery({
    queryKey: ["report", projectId],
    queryFn: () => getReport(projectId),
    retry: false,
    enabled: projectQuery.data?.status === "completed",
  });

  const project = projectQuery.data;
  const report = reportQuery.data;
  const experiments = experimentsQuery.data ?? [];
  const best =
    experiments.find((e) => e.id === report?.best_experiment_id) ??
    experiments.find((e) => e.status === "completed");

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
        <div className="flex flex-wrap items-center gap-3">
          <Link href={`/projects/${projectId}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4" />
              {t("Workspace")}
            </Button>
          </Link>
          <h1 className="text-xl font-semibold text-zinc-900">
            {t("Results")}
          </h1>
          {project ? <Badge variant="secondary">{project.name}</Badge> : null}
        </div>

        {projectQuery.isLoading ||
        (project?.status === "completed" && reportQuery.isLoading) ? (
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-56 md:col-span-2" />
            <Skeleton className="h-72" />
            <Skeleton className="h-72" />
          </div>
        ) : projectQuery.isError ? (
          <ErrorState
            title={t("Could not load results")}
            onRetry={() => projectQuery.refetch()}
          />
        ) : !project || project.status !== "completed" || !report ? (
          <EmptyState
            icon={Trophy}
            title={t("No results yet")}
            description={t(
              "Results appear after the agent finishes the full pipeline. Run it from the workspace.",
            )}
            action={
              <Link href={`/projects/${projectId}`}>
                <Button>{t("Open workspace")}</Button>
              </Link>
            }
          />
        ) : (
          <>
            <Card className="relative overflow-hidden">
              <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-brand/20 blur-3xl" />
              <CardContent className="relative flex flex-wrap items-center gap-6 p-6">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand/15 border border-brand/30">
                  <Trophy className="h-7 w-7 text-brand" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs uppercase tracking-wide text-zinc-500">
                    {t("Best model")}
                  </p>
                  <p className="truncate text-2xl font-semibold text-zinc-900">
                    {t(best?.name ?? report.best_model_type)}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-zinc-600">
                    <Badge variant="secondary">
                      {t(
                        TASK_TYPE_LABELS[report.task.task_type] ??
                          report.task.task_type,
                      )}
                    </Badge>
                    {best?.train_seconds != null ? (
                      <span>
                        {t("trained in")}
                        {t(formatSeconds(best.train_seconds))}
                      </span>
                    ) : null}
                  </div>
                </div>
                <div className="ml-auto text-right">
                  <p className="text-xs uppercase tracking-wide text-zinc-500">
                    {t("validation")}
                    {t(report.task.primary_metric)}
                  </p>
                  <p className="bg-gradient-to-r from-brand to-brand bg-clip-text text-4xl font-bold text-transparent">
                    {formatNumber(
                      report.metrics.find(
                        (m) =>
                          m.name === report.task.primary_metric &&
                          m.split === "validation",
                      )?.value ?? null,
                    )}
                  </p>
                </div>
                <div className="flex w-full flex-wrap gap-2 pt-2 sm:w-auto">
                  <a href={modelDownloadUrl(projectId)}>
                    <Button>
                      <Download className="h-4 w-4" />
                      {t("Download Model")}
                    </Button>
                  </a>
                  <a href={codeDownloadUrl(projectId)}>
                    <Button variant="secondary">
                      <FileCode className="h-4 w-4" />
                      {t("Download Code")}
                    </Button>
                  </a>
                  <Link href={`/projects/${projectId}/predict`}>
                    <Button variant="outline">
                      <Play className="h-4 w-4" />
                      {t("Test Prediction")}
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {t("How models compare —")}
                  {t(report.task.primary_metric)}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <LeaderboardChart experiments={experiments} />
              </CardContent>
            </Card>

            <div className="grid gap-4 lg:grid-cols-2">
              {best?.confusion_matrix ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">
                      {t("Confusion matrix (validation)")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex justify-center">
                    <ConfusionMatrixGrid matrix={best.confusion_matrix} />
                  </CardContent>
                </Card>
              ) : null}
              <Card className={best?.confusion_matrix ? "" : "lg:col-span-2"}>
                <CardHeader>
                  <CardTitle className="text-base">
                    {t("Feature importance")}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <FeatureImportanceChart
                    data={best?.feature_importance ?? []}
                  />
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {t("Improvement history")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ImprovementsList steps={report.improvements} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {t("Why this model won")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-zinc-700">
                  {report.explanation}
                </p>
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
