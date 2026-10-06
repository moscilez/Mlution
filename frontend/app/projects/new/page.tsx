"use client";
import { useI18n } from "@/lib/i18n";
import { useCallback, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  CloudUpload,
  FileSpreadsheet,
  Loader2,
  Minus,
  Plus,
  Sparkles,
  X,
} from "lucide-react";
import { createProject, runProject, uploadDataset } from "@/lib/api";
import { cn, formatBytes } from "@/lib/utils";
import type { DatasetProfile } from "@/lib/types";
import { SiteHeader } from "@/components/site-header";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

const METRIC_OPTIONS: Record<string, { value: string; label: string }[]> = {
  binary_classification: [
    { value: "f1", label: "F1 score" },
    { value: "recall", label: "Recall" },
    { value: "precision", label: "Precision" },
    { value: "roc_auc", label: "ROC AUC" },
    { value: "accuracy", label: "Accuracy" },
  ],
  multiclass_classification: [
    { value: "f1_macro", label: "F1 (macro)" },
    { value: "accuracy", label: "Accuracy" },
  ],
  regression: [
    { value: "rmse", label: "RMSE" },
    { value: "mae", label: "MAE" },
    { value: "r2", label: "R²" },
  ],
};

const DEFAULT_METRIC: Record<string, string> = {
  binary_classification: "f1",
  multiclass_classification: "f1_macro",
  regression: "rmse",
};

function metricOptionsFor(taskHint: string | null) {
  if (taskHint && METRIC_OPTIONS[taskHint]) return METRIC_OPTIONS[taskHint];
  return [
    ...METRIC_OPTIONS.binary_classification,
    ...METRIC_OPTIONS.multiclass_classification.filter(
      (o) =>
        !METRIC_OPTIONS.binary_classification.some((b) => b.value === o.value),
    ),
    ...METRIC_OPTIONS.regression,
  ];
}

export default function NewProjectPage() {
  const { t } = useI18n();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [useDemo, setUseDemo] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const [projectId, setProjectId] = useState<string | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);

  const [targetColumn, setTargetColumn] = useState("");
  const [primaryMetric, setPrimaryMetric] = useState("");
  const [timeBudget, setTimeBudget] = useState(180);
  const [maxExperiments, setMaxExperiments] = useState(4);
  const [businessPriority, setBusinessPriority] = useState("");

  const [busy, setBusy] = useState<"upload" | "run" | "demo" | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const metricOptions = useMemo(
    () => metricOptionsFor(profile?.task_hint ?? null),
    [profile],
  );

  const validateBasics = useCallback((): boolean => {
    const next: Record<string, string> = {};
    if (!name.trim()) next.name = "Project name is required.";
    if (!description.trim())
      next.description =
        "Describe the task so the agent knows what to optimize.";
    setErrors(next);
    return Object.keys(next).length === 0;
  }, [name, description]);

  const onFilePicked = (picked: File | null) => {
    if (!picked) return;
    if (!picked.name.toLowerCase().endsWith(".csv")) {
      setErrors((e) => ({ ...e, file: "Only CSV files are supported." }));
      return;
    }
    setErrors((e) => {
      const { file: _omit, ...rest } = e;
      return rest;
    });
    setFile(picked);
  };

  const handleUploadAnalyze = async () => {
    if (!validateBasics()) return;
    if (!file) {
      setErrors((e) => ({
        ...e,
        file: "Choose a CSV file first, or enable the demo dataset.",
      }));
      return;
    }
    setBusy("upload");
    setErrors({});
    try {
      const project = await createProject({
        name: name.trim(),
        description: description.trim(),
        use_demo_dataset: false,
        target_column: null,
        primary_metric: null,
      });
      const prof = await uploadDataset(project.id, file);
      setProjectId(project.id);
      setProfile(prof);
      setTargetColumn(prof.target_column ?? "");
      setPrimaryMetric(
        (prof.task_hint && DEFAULT_METRIC[prof.task_hint]) ||
          metricOptionsFor(prof.task_hint)[0].value,
      );
    } catch (err) {
      setErrors({
        submit: err instanceof Error ? err.message : "Upload failed.",
      });
    } finally {
      setBusy(null);
    }
  };

  const handleRun = async () => {
    if (!projectId || !profile) return;
    if (!targetColumn) {
      setErrors({ target: "Pick the column the model should predict." });
      return;
    }
    setBusy("run");
    setErrors({});
    try {
      await runProject(projectId, {
        target_column: targetColumn,
        primary_metric: primaryMetric || null,
        business_priority: businessPriority.trim() || null,
        time_budget_seconds: timeBudget,
        max_experiments: maxExperiments,
      });
      router.push(`/projects/${projectId}`);
    } catch (err) {
      setErrors({
        submit: err instanceof Error ? err.message : "Could not start the run.",
      });
      setBusy(null);
    }
  };

  const handleDemoRun = async () => {
    if (!validateBasics()) return;
    setBusy("demo");
    setErrors({});
    try {
      const project = await createProject({
        name: name.trim(),
        description: description.trim(),
        use_demo_dataset: true,
        target_column: null,
        primary_metric: null,
      });
      await runProject(project.id, {
        target_column: null,
        primary_metric: null,
        business_priority: null,
        time_budget_seconds: 180,
        max_experiments: 4,
      });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setErrors({
        submit:
          err instanceof Error ? err.message : "Could not start the demo run.",
      });
      setBusy(null);
    }
  };

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto max-w-3xl space-y-8 px-4 py-10 sm:px-6">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-zinc-600 transition-colors hover:text-zinc-900"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("Back to dashboard")}
        </Link>

        <PageHeader
          title={t("Create project")}
          description={t(
            "Describe the task, provide a dataset, and let the agent build the solution.",
          )}
        />

        {/* Basics */}
        <Card>
          <CardHeader>
            <CardTitle>{t("Task")}</CardTitle>
            <CardDescription>
              {t("What should the model learn to predict?")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">{t("Project name")}</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t("Customer churn predictor")}
                disabled={busy !== null || profile !== null}
              />
              {errors.name ? (
                <p className="text-xs text-red-700">{t(errors.name)}</p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">{t("Task description")}</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t(
                  "Example: Predict whether a telecom customer will churn next month based on their contract, usage and support history. Catching churners early matters more than overall accuracy.",
                )}
                rows={4}
                disabled={busy !== null || profile !== null}
              />
              {errors.description ? (
                <p className="text-xs text-red-700">{t(errors.description)}</p>
              ) : null}
            </div>
          </CardContent>
        </Card>

        {/* Dataset */}
        <Card>
          <CardHeader>
            <CardTitle>{t("Dataset")}</CardTitle>
            <CardDescription>
              {t("Upload a CSV, or use the built-in churn demo dataset.")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-zinc-200 bg-zinc-100 px-4 py-3 transition-colors hover:border-zinc-200">
              <input
                type="checkbox"
                checked={useDemo}
                onChange={(e) => {
                  setUseDemo(e.target.checked);
                  setErrors((prev) => {
                    const { file: _omit, ...rest } = prev;
                    return rest;
                  });
                }}
                disabled={busy !== null || profile !== null}
                className="h-4 w-4 rounded border-zinc-200 bg-zinc-100 accent-brand"
              />
              <div>
                <p className="text-sm font-medium text-zinc-900">
                  {t("Use built-in churn demo dataset")}
                </p>
                <p className="text-xs text-zinc-500">
                  {t(
                    "A realistic telecom churn CSV, loaded and analyzed automatically.",
                  )}
                </p>
              </div>
            </label>

            {!useDemo ? (
              <>
                <div
                  role="button"
                  tabIndex={0}
                  aria-label={t("Upload CSV")}
                  onClick={() => !profile && fileInputRef.current?.click()}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ")
                      fileInputRef.current?.click();
                  }}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOver(false);
                    if (!profile)
                      onFilePicked(e.dataTransfer.files?.[0] ?? null);
                  }}
                  className={cn(
                    "flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-all",
                    dragOver
                      ? "border-brand/60 bg-brand/10"
                      : "border-zinc-200 bg-zinc-100 hover:border-zinc-200",
                    profile && "pointer-events-none opacity-60",
                  )}
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-brand/25 bg-brand/10">
                    <CloudUpload className="h-6 w-6 text-brand" />
                  </div>
                  {file ? (
                    <div className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-zinc-100 px-4 py-2">
                      <FileSpreadsheet className="h-4 w-4 text-accent" />
                      <span className="text-sm text-zinc-900">{file.name}</span>
                      <span className="text-xs text-zinc-500">
                        {t(formatBytes(file.size))}
                      </span>
                      {!profile ? (
                        <button
                          type="button"
                          aria-label={t("Remove file")}
                          onClick={(e) => {
                            e.stopPropagation();
                            setFile(null);
                          }}
                          className="rounded-md p-1 text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-800"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      ) : null}
                    </div>
                  ) : (
                    <>
                      <p className="text-sm font-medium text-zinc-800">
                        {t("Drag and drop your CSV here")}
                      </p>
                      <p className="text-xs text-zinc-500">
                        {t("or click to browse your files")}
                      </p>
                    </>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="hidden"
                  onChange={(e) => onFilePicked(e.target.files?.[0] ?? null)}
                />
                {errors.file ? (
                  <p className="text-xs text-red-700">{t(errors.file)}</p>
                ) : null}

                {!profile ? (
                  <div className="flex justify-end">
                    <Button
                      onClick={handleUploadAnalyze}
                      disabled={busy !== null || !file}
                      variant="secondary"
                    >
                      {busy === "upload" ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Sparkles className="h-4 w-4" />
                      )}
                      {t("Upload and analyze")}
                    </Button>
                  </div>
                ) : null}
              </>
            ) : (
              <div className="rounded-2xl border border-accent/20 bg-accent/5 px-5 py-4 text-sm text-zinc-700">
                {t(
                  "The demo path creates the project, loads the churn dataset and starts the agent with sensible defaults — one click, end to end.",
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Detected columns + run config */}
        {profile ? (
          <Card className="animate-fade-up">
            <CardHeader>
              <CardTitle>{t("Detected dataset")}</CardTitle>
              <CardDescription>
                {t(profile.n_rows.toLocaleString())}
                {t("rows,")}
                {t(profile.n_columns)}
                {t(" ")}
                {t("columns")}
                {t(
                  profile.task_hint
                    ? ` — looks like ${profile.task_hint.replaceAll("_", " ")}`
                    : "",
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="overflow-hidden rounded-xl border border-zinc-200">
                <table className="w-full text-sm">
                  <thead className="bg-zinc-100 text-xs uppercase tracking-wider text-zinc-600">
                    <tr>
                      <th className="px-3 py-2 text-left font-semibold">
                        {t("Column")}
                      </th>
                      <th className="px-3 py-2 text-left font-semibold">
                        {t("Kind")}
                      </th>
                      <th className="px-3 py-2 text-right font-semibold">
                        {t("Missing")}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {profile.columns.slice(0, 8).map((col) => (
                      <tr key={col.name} className="border-t border-zinc-200">
                        <td className="px-3 py-2 font-medium text-zinc-800">
                          {col.name}
                        </td>
                        <td className="px-3 py-2">
                          <Badge
                            variant={
                              col.kind === "numeric"
                                ? "info"
                                : col.kind === "categorical"
                                  ? "default"
                                  : "secondary"
                            }
                          >
                            {t(col.kind.replace("_", "-"))}
                          </Badge>
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums text-zinc-600">
                          {t(col.missing_pct.toFixed(1))}
                          {t("%")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {profile.columns.length > 8 ? (
                  <p className="border-t border-zinc-200 px-3 py-2 text-xs text-zinc-500">
                    {t("plus")}
                    {t(profile.columns.length - 8)}
                    {t("more columns")}
                  </p>
                ) : null}
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="target">{t("Target column")}</Label>
                  <Select
                    id="target"
                    value={targetColumn}
                    onChange={(e) => setTargetColumn(e.target.value)}
                  >
                    <option value="" disabled>
                      {t("Select target")}
                    </option>
                    {profile.columns.map((col) => (
                      <option key={col.name} value={col.name}>
                        {col.name}
                      </option>
                    ))}
                  </Select>
                  {errors.target ? (
                    <p className="text-xs text-red-700">{t(errors.target)}</p>
                  ) : null}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="metric">{t("Primary metric")}</Label>
                  <Select
                    id="metric"
                    value={primaryMetric}
                    onChange={(e) => setPrimaryMetric(e.target.value)}
                  >
                    {metricOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {t(option.label)}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="budget">
                    {t("Time budget —")}
                    {t(" ")}
                    <span className="text-zinc-600">
                      {t(timeBudget)}
                      {t("s")}
                    </span>
                  </Label>
                  <input
                    id="budget"
                    type="range"
                    min={30}
                    max={600}
                    step={30}
                    value={timeBudget}
                    onChange={(e) => setTimeBudget(Number(e.target.value))}
                    className="mt-3 w-full"
                  />
                  <div className="flex justify-between text-[10px] text-zinc-500">
                    <span>{t("30s")}</span>
                    <span>{t("600s")}</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>{t("Max experiments")}</Label>
                  <div className="flex items-center gap-3">
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-9 w-9"
                      aria-label={t("Fewer experiments")}
                      onClick={() =>
                        setMaxExperiments((v) => Math.max(3, v - 1))
                      }
                      disabled={maxExperiments <= 3}
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                    <span className="w-8 text-center text-lg font-semibold tabular-nums">
                      {t(maxExperiments)}
                    </span>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-9 w-9"
                      aria-label={t("More experiments")}
                      onClick={() =>
                        setMaxExperiments((v) => Math.min(6, v + 1))
                      }
                      disabled={maxExperiments >= 6}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="priority">
                  {t("Business priority (optional)")}
                </Label>
                <Input
                  id="priority"
                  value={businessPriority}
                  onChange={(e) => setBusinessPriority(e.target.value)}
                  placeholder={t(
                    'e.g. "maximize recall" or "avoid false positives"',
                  )}
                />
              </div>

              {errors.submit ? (
                <p className="rounded-xl border border-red-400/20 bg-red-400/5 px-4 py-2 text-sm text-red-700">
                  {t(errors.submit)}
                </p>
              ) : null}

              <div className="flex justify-end">
                <Button
                  size="lg"
                  onClick={handleRun}
                  disabled={busy !== null}
                  className="group"
                >
                  {busy === "run" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                  )}
                  {t("Run agent")}
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}

        {/* Demo shortcut */}
        {!profile ? (
          <Card className="border-brand/20 bg-gradient-to-br from-brand/10 via-card to-card">
            <CardContent className="flex flex-col items-start justify-between gap-4 p-6 sm:flex-row sm:items-center">
              <div>
                <p className="font-semibold text-zinc-900">
                  {t("Just want to see it work?")}
                </p>
                <p className="text-sm text-zinc-600">
                  {t(
                    "Create the project and run the agent on the demo dataset in one click.",
                  )}
                </p>
              </div>
              <Button
                variant="secondary"
                onClick={handleDemoRun}
                disabled={busy !== null}
                className="shrink-0"
              >
                {busy === "demo" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                {t("Create and run with demo dataset")}
              </Button>
            </CardContent>
          </Card>
        ) : null}
        {!profile && errors.submit ? (
          <p className="rounded-xl border border-red-400/20 bg-red-400/5 px-4 py-2 text-sm text-red-700">
            {t(errors.submit)}
          </p>
        ) : null}
      </main>
    </div>
  );
}
