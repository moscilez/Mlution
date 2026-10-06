# Agent pipeline

1. **Analyze / DataAnalystAgent:** trusted CSV profiling, missing values, duplicates, class distribution, ID and leakage warnings.
2. **Plan / TaskPlannerAgent + FeatureEngineeringAgent:** choose target/task/real metric; remove exact duplicate rows and missing targets; encode class labels; drop constants, IDs and leakage candidates; build preprocessing.
3. **Build baseline / ModelBuilderAgent + ExperimentAgent:** a real dummy baseline followed by bounded linear/logistic, random forest and optional boosting families. Use fixed random_state=42. Stratify supported classification splits; regression uses random split. Fit imputers/encoders/scalers on train data only.
4. **Evaluate:** compare measured train and validation scores. Classification includes accuracy/precision/recall/F1, applicable ROC-AUC and confusion matrix; regression includes MAE/RMSE/R²/median absolute error. Persist durations and parameters.
5. **Critique / CriticAgent:** examine imbalance and train–validation gaps; propose a curated safe improvement.
6. **Improve:** apply only a trusted model configuration, within remaining slots/budget. Persist hypothesis/action/before/after/decision. No generated code executes on the server.
7. **Finalize / ReportAgent:** select the winner from this run, save its preprocessing/model bundle, real leaderboard and report, and generate downloadable inference code. Narrative LLM is optional with a deterministic fallback.

SupervisorAgent controls stage transitions and catches failures. RQ controls process timeout and shutdown. Persisted AgentRun ID is the event correlation ID. Cancellation is checked before stage transitions, messages and experiments, and after fitting. Failed experiments do not kill the entire run when another model succeeds. Pipeline failures produce safe UI errors while full details stay in backend logs. Reruns do not mix historical experiments into model selection.

MVP deliberately keeps fitted state inside the worker process. Full retry repeats all dependent stages with a new ID. There is no automatic training retry; transient queue failures are explicit so expensive work cannot silently duplicate. LLM errors fall back to templates.
