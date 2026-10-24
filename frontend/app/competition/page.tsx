"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Download,
  FlaskConical,
  Play,
  Square,
  Upload,
  FileCheck2,
} from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/lib/i18n";
import { API_BASE, cancelRun, getRuns, listProjects, request } from "@/lib/api";

interface Trial {
  index: number;
  dummy: boolean;
  status: string;
  decision?: string;
  score?: number;
  train_score?: number;
  seconds?: number;
  error?: string;
  plan: {
    algorithm: string;
    hypothesis: string;
    rationale: string;
    features: string;
    source: string;
  };
}
interface Research {
  mode: string;
  checkpoint: string;
  profile: {
    target: string;
    metric: string;
    train_rows: number;
    test_rows: number;
    classes?: number;
  };
  experiments: Trial[];
  best?: Trial;
  elapsed_seconds: number;
  llm_calls: number;
  llm_tokens_reserved: number;
}
interface State {
  project: {
    id: string;
    name: string;
    status: string;
    error: string | null;
    stage: string | null;
  };
  research: Research | null;
}

export default function CompetitionPage() {
  const { locale, t } = useI18n();
  const ru = locale === "ru";
  const cache = useQueryClient();
  const [id, setId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<Record<string, File>>({});
  const [budget, setBudget] = useState(10800);
  const [count, setCount] = useState(24);
  const [offline, setOffline] = useState(true);
  useEffect(() => {
    setId(new URLSearchParams(window.location.search).get("project") ?? "");
  }, []);
  const projects = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const state = useQuery({
    queryKey: ["competition", id],
    queryFn: () => request<State>(`/api/competition/projects/${id}`),
    enabled: !!id,
    refetchInterval: 2500,
  });
  const active =
    state.data?.project.status === "queued" ||
    state.data?.project.status === "running";
  const runs = useQuery({
    queryKey: ["runs", id],
    queryFn: () => getRuns(id),
    enabled: !!id,
    refetchInterval: active ? 2500 : false,
  });
  function select(project: string) {
    setId(project);
    window.history.replaceState(
      null,
      "",
      project
        ? `/competition?project=${encodeURIComponent(project)}`
        : "/competition",
    );
  }
  const upload = useMutation({
    mutationFn: async () => {
      const body = new FormData();
      body.append("name", name);
      body.append("description", description);
      for (const key of ["train", "test", "dictionary", "sample"])
        body.append(key, files[key]);
      return request<{ project: { id: string } }>("/api/competition/projects", {
        method: "POST",
        body,
      });
    },
    onSuccess: (data) => {
      select(data.project.id);
      void cache.invalidateQueries({ queryKey: ["projects"] });
    },
  });
  const run = useMutation({
    mutationFn: () =>
      request(`/api/competition/projects/${id}/run`, {
        method: "POST",
        body: JSON.stringify({
          time_budget_seconds: budget,
          max_experiments: count,
          offline,
          threads: 8,
          trial_timeout_seconds: Math.min(1200, budget),
          max_llm_calls: 16,
          max_llm_tokens: 24000,
        }),
      }),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["competition", id] });
      void cache.invalidateQueries({ queryKey: ["runs", id] });
    },
  });
  const cancel = useMutation({
    mutationFn: async () => {
      const running = runs.data?.find((item) =>
        ["queued", "running"].includes(item.status),
      );
      if (running) await cancelRun(id, running.id);
    },
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["competition", id] });
    },
  });
  const research = state.data?.research;
  const problem = upload.error || run.error || cancel.error || state.error;
  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-6xl space-y-7 px-4 py-10 sm:px-6">
        <PageHeader
          title="AutoResearch"
          description={
            ru
              ? "Конкурсный агент: от материалов задачи до файла предсказаний."
              : "Competition agent: from task materials to a prediction file."
          }
          actions={
            <Button variant="outline" onClick={() => select("")}>
              {ru ? "Новая задача" : "New task"}
            </Button>
          }
        />
        <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-zinc-200 bg-white p-4 text-xs text-zinc-600">
          <FlaskConical size={18} className="text-brand" />
          <span>Python 3.12</span>
          <span>8 CPU · 32 GB</span>
          <span>{ru ? "До 3 часов на задачу" : "Up to 3 hours per task"}</span>
          <span>Qwen3.8-27B</span>
        </div>
        <label className="block space-y-2 text-sm">
          <span>{ru ? "Мои конкурсные задачи" : "My competition tasks"}</span>
          <select
            className="w-full rounded-xl border bg-white p-3"
            value={id}
            onChange={(event) => select(event.target.value)}
          >
            <option value="">
              {ru ? "Загрузить новую задачу" : "Upload a new task"}
            </option>
            {projects.data
              ?.filter((project) => project.mode === "competition")
              .map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
          </select>
        </label>
        {problem && (
          <p
            role="alert"
            className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
          >
            {problem instanceof Error
              ? t(problem.message)
              : t("Request failed")}
          </p>
        )}
        {!id ? (
          <Card>
            <CardHeader>
              <CardTitle>
                {ru ? "Материалы задачи" : "Task materials"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form
                className="space-y-5"
                onSubmit={(event) => {
                  event.preventDefault();
                  upload.mutate();
                }}
              >
                <label className="block space-y-2 text-sm">
                  <span>{ru ? "Название задачи" : "Task name"}</span>
                  <Input
                    required
                    maxLength={120}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                  />
                </label>
                <label className="block space-y-2 text-sm">
                  <span>
                    {ru
                      ? "Условие из task.md: цель, метрика и формат результата"
                      : "Task.md contents: objective, metric and output format"}
                  </span>
                  <Textarea
                    required
                    maxLength={40000}
                    rows={7}
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                  />
                </label>
                <div className="grid gap-4 sm:grid-cols-2">
                  {[
                    ["train", "train.csv"],
                    ["test", "test.csv"],
                    ["dictionary", "data_dictionary.csv"],
                    ["sample", "sample_submission.csv"],
                  ].map(([key, label]) => (
                    <label
                      key={key}
                      className="block space-y-3 rounded-xl border border-dashed border-zinc-300 p-4 text-sm"
                    >
                      <span className="flex items-center gap-2">
                        <FileCheck2 size={16} className="text-brand" />
                        {label}
                      </span>
                      <input
                        required
                        type="file"
                        accept=".csv,text/csv"
                        className="block w-full min-w-0 text-xs file:mr-3 file:rounded-full file:border-0 file:bg-zinc-100 file:px-3 file:py-2"
                        onChange={(event) => {
                          const file = event.target.files?.[0];
                          setFiles((current) => {
                            const next = { ...current };
                            if (file) next[key] = file;
                            else delete next[key];
                            return next;
                          });
                        }}
                      />
                    </label>
                  ))}
                </div>
                <p className="text-xs leading-relaxed text-zinc-500">
                  {ru
                    ? "Цель и идентификаторы определяются по train, test и шаблону сабмита. ID и порядок строк шаблона сохраняются. Скрытые целевые значения не используются."
                    : "Target and identifiers are inferred from train, test and sample submission. Template identifiers and row order are preserved; hidden labels are never used."}
                </p>
                <Button
                  type="submit"
                  disabled={upload.isPending || Object.keys(files).length !== 4}
                >
                  <Upload size={16} />
                  {upload.isPending
                    ? t("Please wait…")
                    : ru
                      ? "Проверить и создать задачу"
                      : "Validate and create task"}
                </Button>
              </form>
            </CardContent>
          </Card>
        ) : state.data ? (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-xl font-semibold">
                {state.data.project.name}
              </h2>
              <StatusBadge status={state.data.project.status} />
              {state.data.project.stage && (
                <span className="text-xs text-zinc-500">
                  {t(state.data.project.stage)}
                </span>
              )}
            </div>
            {state.data.project.error && (
              <p role="alert" className="text-sm text-red-700">
                {state.data.project.error}
              </p>
            )}
            <Card>
              <CardContent className="space-y-5 pt-6">
                <div className="grid gap-5 sm:grid-cols-2">
                  <label className="space-y-2 text-sm">
                    <span>
                      {ru ? "Бюджет времени, секунды" : "Time budget, seconds"}
                    </span>
                    <Input
                      type="number"
                      min={30}
                      max={10800}
                      disabled={active}
                      value={budget}
                      onChange={(event) =>
                        setBudget(Number(event.target.value))
                      }
                    />
                  </label>
                  <label className="space-y-2 text-sm">
                    <span>
                      {ru ? "Максимум экспериментов" : "Maximum experiments"}
                    </span>
                    <Input
                      type="number"
                      min={2}
                      max={64}
                      disabled={active}
                      value={count}
                      onChange={(event) => setCount(Number(event.target.value))}
                    />
                  </label>
                </div>
                <label className="flex items-start gap-3 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    disabled={active}
                    checked={offline}
                    onChange={(event) => setOffline(event.target.checked)}
                  />
                  <span>
                    {ru
                      ? "Локальная проверка без LLM"
                      : "Local smoke test without LLM"}
                    <span className="mt-1 block text-xs leading-relaxed text-zinc-500">
                      {ru
                        ? "Это эвристический режим. Для агентного запуска снимите флажок и настройте API Qwen организаторов на сервере."
                        : "This is a heuristic mode. For an agent run, uncheck and configure the organizer Qwen API on the server."}
                    </span>
                  </span>
                </label>
                <div className="flex flex-wrap gap-3">
                  {active ? (
                    <Button
                      variant="outline"
                      disabled={cancel.isPending}
                      onClick={() => cancel.mutate()}
                    >
                      <Square size={14} />
                      {t("Cancel run")}
                    </Button>
                  ) : (
                    <Button
                      disabled={
                        run.isPending ||
                        budget < 30 ||
                        budget > 10800 ||
                        count < 2 ||
                        count > 64
                      }
                      onClick={() => run.mutate()}
                    >
                      <Play size={16} />
                      {ru ? "Запустить исследование" : "Start research"}
                    </Button>
                  )}
                  {research && (
                    <>
                      <a
                        href={`${API_BASE}/api/competition/projects/${id}/submission`}
                        className="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm text-brand"
                      >
                        <Download size={15} />
                        {ru ? "Скачать предсказания" : "Download predictions"}
                      </a>
                      <a
                        href={`${API_BASE}/api/competition/projects/${id}/research`}
                        className="inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm"
                      >
                        research.json
                      </a>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
            {research && (
              <>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  {[
                    [ru ? "Цель" : "Target", research.profile.target],
                    [ru ? "Метрика" : "Metric", research.profile.metric],
                    [
                      ru
                        ? "Лучший результат валидации"
                        : "Best validation score",
                      research.best?.score?.toFixed(5) ?? "—",
                    ],
                    [
                      ru ? "Обращения к LLM" : "LLM calls",
                      String(research.llm_calls),
                    ],
                  ].map(([label, value]) => (
                    <Card className="min-w-0 p-4" key={label}>
                      <p className="text-xs text-zinc-500">{label}</p>
                      <p className="mt-2 break-words font-semibold">{value}</p>
                    </Card>
                  ))}
                </div>
                <p className="text-xs text-zinc-500">
                  {research.mode === "offline_heuristic"
                    ? ru
                      ? "Режим: локальные эвристики"
                      : "Mode: local heuristics"
                    : "Qwen AutoResearch"}{" "}
                  · {Math.round(research.elapsed_seconds)} {ru ? "с" : "s"} ·{" "}
                  {ru
                    ? "Резервный файл предсказаний доступен во время исследования. Метрика валидации не является оценкой скрытого теста."
                    : "A prediction checkpoint is available during research. Validation quality is not a hidden-test score."}
                </p>
                <Card>
                  <CardHeader>
                    <CardTitle>
                      {ru
                        ? "Гипотезы и эксперименты"
                        : "Hypotheses and experiments"}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {research.experiments.map((item) => (
                      <article
                        key={item.index}
                        className="space-y-2 rounded-xl border border-zinc-200 p-4"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs text-zinc-500">
                            #{item.index + 1}
                          </span>
                          <strong className="text-sm">
                            {item.dummy
                              ? "Dummy baseline"
                              : item.plan.algorithm}
                          </strong>
                          <StatusBadge status={item.status} />
                          <span className="text-xs text-zinc-500">
                            {item.plan.source}
                          </span>
                          {item.decision && (
                            <span
                              className={
                                item.decision === "accept"
                                  ? "text-xs text-emerald-700"
                                  : "text-xs text-zinc-500"
                              }
                            >
                              {item.decision === "accept"
                                ? ru
                                  ? "Принята"
                                  : "Accepted"
                                : ru
                                  ? "Отклонена"
                                  : "Rejected"}
                            </span>
                          )}
                        </div>
                        <p className="text-sm">{item.plan.hypothesis}</p>
                        <p className="text-xs leading-relaxed text-zinc-500">
                          {item.plan.rationale}
                        </p>
                        <div className="flex flex-wrap gap-4 text-xs text-zinc-600">
                          <span>
                            {t("Train")}: {item.train_score?.toFixed(5) ?? "—"}
                          </span>
                          <span>
                            {t("Validation")}: {item.score?.toFixed(5) ?? "—"}
                          </span>
                          <span>{item.plan.features}</span>
                          {item.seconds !== undefined && (
                            <span>{item.seconds.toFixed(1)} s</span>
                          )}
                          {item.error && (
                            <span className="text-red-700">{item.error}</span>
                          )}
                        </div>
                      </article>
                    ))}
                  </CardContent>
                </Card>
              </>
            )}
          </>
        ) : (
          <p role="status" className="py-8 text-sm text-zinc-500">
            {t("Please wait…")}
          </p>
        )}
      </main>
    </>
  );
}
