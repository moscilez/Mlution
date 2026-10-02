export type ProjectStatus = "created" | "running" | "completed" | "failed";

export type TaskType =
  | "binary_classification"
  | "multiclass_classification"
  | "regression";

export interface Project {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  stage: string | null;
  task_type: TaskType | null;
  target_column: string | null;
  primary_metric: string | null;
  best_experiment_id: string | null;
  best_metric_value: number | null;
  best_model_type: string | null;
  dataset_name: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ColumnProfile {
  name: string;
  dtype: string;
  kind: "numeric" | "categorical" | "id_like";
  n_missing: number;
  missing_pct: number;
  n_unique: number;
  examples: string[];
}

export interface Warning {
  level: "info" | "warning" | "critical";
  code: string;
  message: string;
}

export interface LeakageCandidate {
  column: string;
  reason: string;
}

export interface DatasetProfile {
  n_rows: number;
  n_columns: number;
  columns: ColumnProfile[];
  n_duplicates: number;
  duplicate_pct: number;
  numeric_columns: string[];
  categorical_columns: string[];
  id_columns: string[];
  leakage_candidates: LeakageCandidate[];
  target_column: string | null;
  task_hint: string | null;
  class_balance: Record<string, number> | null;
  imbalance_warning: boolean;
  warnings: Warning[];
}

export interface MLTask {
  task_type: string;
  target_column: string;
  primary_metric: string;
  secondary_metrics: string[];
  business_priority: string | null;
  rationale: string;
}

export interface MetricResult {
  name: string;
  value: number;
  split: "train" | "validation";
}

export interface ConfusionMatrix {
  labels: string[];
  matrix: number[][];
}

export interface FeatureImportance {
  feature: string;
  importance: number;
}

export type ExperimentStatus = "pending" | "running" | "completed" | "failed";
export type ExperimentStage = "baseline" | "improvement";

export interface Experiment {
  id: string;
  project_id: string;
  name: string;
  model_type: string;
  status: ExperimentStatus;
  stage: ExperimentStage;
  hyperparameters: Record<string, unknown>;
  metrics: MetricResult[];
  primary_metric_name: string | null;
  primary_metric_value: number | null;
  train_seconds: number | null;
  error: string | null;
  feature_importance: FeatureImportance[];
  confusion_matrix: ConfusionMatrix | null;
  created_at: string;
}

export type EventLevel = "info" | "success" | "warning" | "error";

export interface AgentEvent {
  id: number;
  project_id: string;
  ts: string;
  agent: string;
  stage: string;
  level: EventLevel;
  message: string;
  data: Record<string, unknown> | null;
}

export interface ImprovementStep {
  hypothesis: string;
  reason: string;
  action: string;
  before: Record<string, number>;
  after: Record<string, number>;
  decision: "accept_improvement" | "reject_improvement";
  details: string | null;
}

export interface PredictionResponse {
  prediction: unknown;
  probability: number | null;
  probabilities: Record<string, number> | null;
  model_type: string;
  explanation: string;
  top_factors: FeatureImportance[];
}

export interface LeaderboardEntry {
  experiment_id: string;
  model_type: string;
  stage: string;
  primary_metric_value: number;
}

export interface FinalReport {
  summary: string;
  task: MLTask;
  best_experiment_id: string;
  best_model_type: string;
  metrics: MetricResult[];
  leaderboard: LeaderboardEntry[];
  improvements: ImprovementStep[];
  warnings: Warning[];
  limitations: string[];
  next_steps: string[];
  explanation: string;
  usage_code: string;
  generated_at: string;
}

export type StageStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped";

export interface StageInfo {
  name: string;
  status: StageStatus;
  started_at: string | null;
  finished_at: string | null;
}

export interface RunStatus {
  project_id: string;
  status: string;
  stage: string | null;
  stages: StageInfo[];
  progress: number;
  error: string | null;
}

export interface ChatReply {
  reply: string;
  ts: string;
}

export const STAGE_ORDER = [
  "analyze",
  "plan",
  "build_baseline",
  "evaluate",
  "critique",
  "improve",
  "finalize",
] as const;

export const STAGE_LABELS: Record<string, string> = {
  analyze: "Analyze",
  plan: "Plan",
  build_baseline: "Baseline",
  evaluate: "Evaluate",
  critique: "Critique",
  improve: "Improve",
  finalize: "Finalize",
};

export const TASK_TYPE_LABELS: Record<string, string> = {
  binary_classification: "Binary classification",
  multiclass_classification: "Multiclass classification",
  regression: "Regression",
};
