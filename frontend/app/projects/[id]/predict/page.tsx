"use client";
import { useI18n } from "@/lib/i18n";
import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Loader2, Play, Wand2 } from "lucide-react";
import { getProfile, getProject, predict } from "@/lib/api";
import { formatPercent } from "@/lib/utils";
import type { PredictionResponse } from "@/lib/types";
import { SiteHeader } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";

export default function PlaygroundPage() {
  const { t } = useI18n();
  const projectId = useParams<{ id: string }>().id;
  const [values, setValues] = useState<Record<string, string>>({});

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });
  const profileQuery = useQuery({
    queryKey: ["profile", projectId],
    queryFn: () => getProfile(projectId),
    retry: false,
  });

  const predictMutation = useMutation({
    mutationFn: (features: Record<string, unknown>) =>
      predict(projectId, features),
  });

  const profile = profileQuery.data;
  const leakageCols = useMemo(
    () => new Set((profile?.leakage_candidates ?? []).map((c) => c.column)),
    [profile],
  );
  const formColumns = useMemo(
    () =>
      (profile?.columns ?? []).filter(
        (c) =>
          c.kind !== "id_like" &&
          c.n_unique > 1 &&
          c.name !==
            (projectQuery.data?.target_column ?? profile?.target_column) &&
          !leakageCols.has(c.name),
      ),
    [profile, leakageCols, projectQuery.data?.target_column],
  );

  function submit() {
    const features: Record<string, unknown> = {};
    for (const col of formColumns) {
      const raw = values[col.name];
      if (raw === undefined || raw === "") continue;
      features[col.name] = col.kind === "numeric" ? Number(raw) : raw;
    }
    predictMutation.mutate(features);
  }

  const result: PredictionResponse | undefined = predictMutation.data;
  const ready = projectQuery.data?.status === "completed";

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
        <div className="flex flex-wrap items-center gap-3">
          <Link href={`/projects/${projectId}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4" />
              {t("Workspace")}
            </Button>
          </Link>
          <h1 className="text-xl font-semibold text-zinc-900">
            {t("Prediction Playground")}
          </h1>
        </div>

        {projectQuery.isLoading || profileQuery.isLoading ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <Skeleton className="h-96" />
            <Skeleton className="h-96" />
          </div>
        ) : projectQuery.isError ? (
          <ErrorState
            title={t("Could not load project")}
            onRetry={() => projectQuery.refetch()}
          />
        ) : !ready ? (
          <EmptyState
            icon={Wand2}
            title={t("Model not trained yet")}
            description={t(
              "The playground unlocks once the pipeline completes and a best model is selected.",
            )}
            action={
              <Link href={`/projects/${projectId}`}>
                <Button>{t("Open workspace")}</Button>
              </Link>
            }
          />
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {t("Input features")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {formColumns.map((col) => (
                  <div key={col.name} className="space-y-1.5">
                    <Label htmlFor={`f-${col.name}`}>
                      {col.name}
                      <span className="ml-2 text-[10px] uppercase tracking-wide text-zinc-500">
                        {t(col.kind)}
                      </span>
                    </Label>
                    {col.kind === "numeric" ? (
                      <Input
                        id={`f-${col.name}`}
                        type="number"
                        step="any"
                        placeholder={col.examples[0] ?? "e.g. 42"}
                        value={values[col.name] ?? ""}
                        onChange={(e) =>
                          setValues((v) => ({
                            ...v,
                            [col.name]: e.target.value,
                          }))
                        }
                      />
                    ) : (
                      <Select
                        id={`f-${col.name}`}
                        value={values[col.name] ?? ""}
                        onChange={(e) =>
                          setValues((v) => ({
                            ...v,
                            [col.name]: e.target.value,
                          }))
                        }
                      >
                        <option value="">{t("(leave empty)")}</option>
                        {col.examples.map((ex) => (
                          <option key={ex} value={ex}>
                            {t(ex)}
                          </option>
                        ))}
                      </Select>
                    )}
                  </div>
                ))}
                <Button
                  className="w-full"
                  onClick={submit}
                  disabled={predictMutation.isPending}
                >
                  {predictMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                  {t("Predict")}
                </Button>
                {predictMutation.isError ? (
                  <p className="rounded-xl border border-red-400/30 bg-red-500/10 p-3 text-xs text-red-700">
                    {predictMutation.error instanceof Error
                      ? predictMutation.error.message
                      : "Prediction failed"}
                  </p>
                ) : null}
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden">
              <div className="pointer-events-none absolute -left-20 -top-20 h-56 w-56 rounded-full bg-accent/10 blur-3xl" />
              <CardHeader>
                <CardTitle className="text-base">{t("Prediction")}</CardTitle>
              </CardHeader>
              <CardContent>
                {!result ? (
                  <div className="flex h-64 flex-col items-center justify-center gap-2 text-center">
                    <Wand2 className="h-8 w-8 text-zinc-500" />
                    <p className="text-sm text-zinc-500">
                      {t("Fill in the features and press Predict.")}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-5">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-zinc-500">
                        {t(
                          result.probability != null
                            ? "Predicted class"
                            : "Predicted value",
                        )}
                      </p>
                      <p className="mt-1 bg-gradient-to-r from-brand to-brand bg-clip-text text-4xl font-bold text-transparent">
                        {t(String(result.prediction))}
                      </p>
                      <p className="mt-1 text-xs text-zinc-500">
                        {t("model:")}
                        {t(result.model_type)}
                      </p>
                    </div>

                    {result.probability != null ? (
                      <div>
                        <div className="mb-1 flex items-center justify-between text-xs text-zinc-600">
                          <span>{t("Probability")}</span>
                          <span className="font-mono text-zinc-800">
                            {t(formatPercent(result.probability))}
                          </span>
                        </div>
                        <div className="h-2.5 overflow-hidden rounded-full bg-zinc-100">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-brand to-brand transition-all duration-500"
                            style={{
                              width: `${Math.round(result.probability * 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    ) : null}

                    {result.probabilities &&
                    Object.keys(result.probabilities).length > 2 ? (
                      <div className="space-y-1.5">
                        {Object.entries(result.probabilities)
                          .sort((a, b) => b[1] - a[1])
                          .map(([label, p]) => (
                            <div
                              key={label}
                              className="flex items-center gap-2 text-xs"
                            >
                              <span className="w-24 truncate text-zinc-600">
                                {t(label)}
                              </span>
                              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-zinc-100">
                                <div
                                  className="h-full rounded-full bg-brand"
                                  style={{ width: `${Math.round(p * 100)}%` }}
                                />
                              </div>
                              <span className="w-12 text-right font-mono text-zinc-700">
                                {t(formatPercent(p))}
                              </span>
                            </div>
                          ))}
                      </div>
                    ) : null}

                    <p className="rounded-xl border border-zinc-200 bg-zinc-100 p-3 text-sm leading-relaxed text-zinc-700">
                      {result.explanation}
                    </p>

                    {result.top_factors.length > 0 ? (
                      <div>
                        <p className="mb-2 text-xs uppercase tracking-wide text-zinc-500">
                          {t("Top factors")}
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {result.top_factors.map((f) => (
                            <span
                              key={f.feature}
                              className="rounded-lg border border-brand/25 bg-brand/10 px-2.5 py-1 text-xs text-zinc-800"
                            >
                              {t(f.feature)}
                              <span className="ml-1.5 font-mono text-brand">
                                {t(formatPercent(f.importance, 0))}
                              </span>
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}
