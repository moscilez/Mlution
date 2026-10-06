"use client";
import Link from "next/link";
import { useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  Database,
  FileText,
  ScanSearch,
  ClipboardList,
  Layers3,
  ChartNoAxesCombined,
  ShieldCheck,
  TrendingUp,
  PackageCheck,
  Download,
  ChevronRight,
} from "lucide-react";
import { Logo } from "@/components/logo";
import { LanguageSwitcher } from "@/components/language-switcher";
import { DemoButton } from "@/components/demo-button";
import { useI18n } from "@/lib/i18n";

const copy = {
  ru: {
    nav: "Возможности",
    process: "Как это работает",
    projects: "Мои проекты",
    start: "Начать проект",
    eyebrow: "ВАШЕ ПРОСТРАНСТВО ДЛЯ МАШИННОГО ОБУЧЕНИЯ",
    title: ["Данные.", "Модели.", "Решения."],
    intro:
      "От первого CSV до модели, которой вы доверяете. Mlution анализирует данные, сравнивает алгоритмы и объясняет каждый шаг.",
    note: "Ваши данные. Понятный процесс. Измеримый результат.",
    preview: "ЗНАКОМСТВО С ПРОЦЕССОМ",
    previewTitle: "Сложная работа.\nПростой путь.",
    previewIntro:
      "Семь этапов, каждый — на виду. Выберите этап и узнайте, что происходит между загрузкой данных и готовым результатом.",
    sample: "Пример проекта · прогноз оттока",
    illustrative: "Иллюстрация процесса · значения для примера",
    input: "Входные данные",
    output: "Результат этапа",
    progress: "Путь к модели",
    rows: "строк",
    columns: "столбцов",
    stages: "7 этапов",
    artifact: "Модель, отчёт и код",
    private: "Доступ только владельцу",
    upload: "Один CSV",
    uploadCaption: "Всё начинается с ваших данных",
    metric: "F1 на валидации",
    featuresTitle: "Больше ясности.\nНа каждом шаге.",
    featuresIntro:
      "Инструменты для вдумчивой работы с данными. В одном спокойном пространстве.",
    featureNames: [
      "Данные под контролем.",
      "Сравнение без догадок.",
      "Результат, который остаётся с вами.",
    ],
    featureBody: [
      "Типы столбцов, пропуски, дубликаты и баланс классов. Вы увидите качество данных до начала обучения.",
      "Базовая модель и кандидаты оцениваются по одной метрике. История экспериментов показывает, что изменилось и почему.",
      "Скачайте модель и Python-код. Изучите отчёт, важность признаков и проверьте предсказания на своих примерах.",
    ],
    ctaTitle: "Ваша следующая модель\nначинается здесь.",
    ctaBody: "Принесите задачу и данные. Остальное пройдём вместе.",
    footer: "От данных к решению.",
    stageNames: [
      "Анализ",
      "План",
      "Базовая модель",
      "Оценка",
      "Проверка",
      "Улучшение",
      "Результат",
    ],
    stageTitles: [
      "Сначала — понять данные.",
      "Правильная цель. Чёткий план.",
      "Точка отсчёта для сравнения.",
      "Качество в цифрах.",
      "Посмотреть глубже метрики.",
      "Менять только то, что помогает.",
      "Готово к следующему шагу.",
    ],
    stageDescriptions: [
      "Агент проверяет структуру CSV, пропуски и дубликаты. Определяет целевой столбец и возможные риски утечки.",
      "Определяет тип задачи, выбирает метрики и способы подготовки данных под вашу цель.",
      "Обучает простую базовую модель и несколько кандидатов, чтобы получить честную точку отсчёта.",
      "Сравнивает метрики обучения и валидации. Показывает, как модель работает на отложенных данных.",
      "Проверяет ошибки, дисбаланс классов и признаки переобучения. Объясняет ограничения результата.",
      "Проверяет гипотезы, меняет параметры и сохраняет изменения, которые улучшают выбранную метрику.",
      "Собирает лучшую модель, отчёт и код для предсказаний. Всё доступно для скачивания.",
    ],
    outputs: [
      "Профиль данных и предупреждения",
      "Тип задачи и основная метрика",
      "Первые обученные модели",
      "Сравнение экспериментов",
      "Риски и ограничения",
      "История улучшений",
      "Модель, Python-код и отчёт",
    ],
    checks: [
      "Пропуски найдены",
      "Дубликаты проверены",
      "Целевой столбец: churn",
    ],
    plan: [
      "Бинарная классификация",
      "Основная метрика: F1",
      "Разделение: обучение / валидация",
    ],
    risk: [
      "Баланс классов",
      "Разрыв качества на выборках",
      "Возможная утечка данных",
    ],
    improved: "Гипотеза → эксперимент → сравнение",
    generated: "Отчёт с метриками и ограничениями",
  },
  en: {
    nav: "Features",
    process: "How it works",
    projects: "My projects",
    start: "Start a project",
    eyebrow: "YOUR SPACE FOR MACHINE LEARNING",
    title: ["Data.", "Models.", "Decisions."],
    intro:
      "From your first CSV to a model you understand. Mlution explores your data, compares algorithms and explains every step.",
    note: "Your data. A clear process. Measurable results.",
    preview: "MEET THE PROCESS",
    previewTitle: "Complex work.\nA clear path.",
    previewIntro:
      "Seven stages, all in view. Select a stage to see what happens between your dataset and your finished model.",
    sample: "Example project · customer churn",
    illustrative: "Process illustration · example values",
    input: "Input dataset",
    output: "Stage output",
    progress: "The path to a model",
    rows: "rows",
    columns: "columns",
    stages: "7 stages",
    artifact: "Model, report and code",
    private: "Owner-only access",
    upload: "One CSV",
    uploadCaption: "It all starts with your data",
    metric: "Validation F1",
    featuresTitle: "More clarity.\nAt every step.",
    featuresIntro:
      "Tools for thoughtful work with data. In one calm workspace.",
    featureNames: [
      "Understand your data.",
      "Compare with confidence.",
      "A result you can take with you.",
    ],
    featureBody: [
      "Column types, missing values, duplicates and class balance. See the quality of your data before training begins.",
      "Baselines and candidates are evaluated on the same metric. Experiment history shows what changed and why.",
      "Download your model and Python code. Explore the report, feature importance and predictions on your own examples.",
    ],
    ctaTitle: "Your next model\nstarts here.",
    ctaBody: "Bring your task and data. We’ll work through the rest together.",
    footer: "From data to decisions.",
    stageNames: [
      "Analyze",
      "Plan",
      "Baseline",
      "Evaluate",
      "Critique",
      "Improve",
      "Finalize",
    ],
    stageTitles: [
      "First, understand the data.",
      "The right goal. A clear plan.",
      "A starting point to compare.",
      "Quality, measured.",
      "Look beyond the score.",
      "Keep changes that help.",
      "Ready for your next step.",
    ],
    stageDescriptions: [
      "The agent checks your CSV structure, missing values and duplicates. It identifies the target and potential leakage.",
      "Identifies the task type, chooses metrics and plans data preparation around your objective.",
      "Trains a simple baseline and candidates to establish a reliable reference point.",
      "Compares training and validation metrics. See how the model performs on held-out data.",
      "Reviews errors, class imbalance and signs of overfitting. Explains the limitations of the result.",
      "Tests hypotheses, adjusts parameters and retains improvements to your chosen metric.",
      "Packages the best model, report and prediction code. Everything is ready to download.",
    ],
    outputs: [
      "Data profile and warnings",
      "Task type and primary metric",
      "First trained models",
      "Experiment comparison",
      "Risks and limitations",
      "Improvement history",
      "Model, Python code and report",
    ],
    checks: [
      "Missing values identified",
      "Duplicates checked",
      "Target column: churn",
    ],
    plan: [
      "Binary classification",
      "Primary metric: F1",
      "Split: training / validation",
    ],
    risk: ["Class balance", "Train / validation gap", "Potential data leakage"],
    improved: "Hypothesis → experiment → comparison",
    generated: "Report with metrics and limitations",
  },
};
const icons = [
  ScanSearch,
  ClipboardList,
  Layers3,
  ChartNoAxesCombined,
  ShieldCheck,
  TrendingUp,
  PackageCheck,
];

export default function LandingPage() {
  const { locale } = useI18n();
  const c = copy[locale];
  const [stage, setStage] = useState(0);
  const StageIcon = icons[stage];
  return (
    <div className="landing">
      <header className="landing-header">
        <div className="landing-nav">
          <Logo />
          <nav
            aria-label={locale === "ru" ? "Главное меню" : "Main navigation"}
          >
            <a href="#process" className="nav-secondary">
              {c.process}
            </a>
            <a href="#features" className="nav-secondary">
              {c.nav}
            </a>
            <LanguageSwitcher />
            <Link href="/dashboard" className="nav-projects">
              {c.projects}
              <ArrowUpRight size={13} />
            </Link>
          </nav>
        </div>
      </header>
      <main>
        <section className="landing-hero">
          <p className="eyebrow">{c.eyebrow}</p>
          <h1>
            {c.title[0]}
            <br />
            {c.title[1]} <span>{c.title[2]}</span>
          </h1>
          <p className="hero-intro">{c.intro}</p>
          <div className="hero-actions">
            <Link href="/projects/new" className="primary-pill">
              {c.start}
              <ArrowRight size={17} />
            </Link>
            <DemoButton />
          </div>
          <p className="hero-note">{c.note}</p>
          <div className="hero-summary">
            {[
              { icon: Database, name: c.upload, body: c.uploadCaption },
              { icon: Layers3, name: c.stages, body: c.progress },
              { icon: PackageCheck, name: c.artifact, body: c.private },
            ].map((item) => (
              <div key={item.name}>
                <item.icon size={20} strokeWidth={1.5} />
                <div>
                  <strong>{item.name}</strong>
                  <span>{item.body}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
        <section id="process" className="process-section">
          <div className="section-heading">
            <p className="eyebrow">{c.preview}</p>
            <h2>{c.previewTitle}</h2>
            <p>{c.previewIntro}</p>
          </div>
          <div
            className="process-stages"
            role="tablist"
            aria-label={c.progress}
          >
            {c.stageNames.map((name, index) => {
              const Icon = icons[index];
              return (
                <button
                  key={index}
                  id={`stage-${index}`}
                  role="tab"
                  aria-selected={stage === index}
                  aria-controls="stage-panel"
                  tabIndex={stage === index ? 0 : -1}
                  onClick={() => setStage(index)}
                  onKeyDown={(event) => {
                    if (
                      ["ArrowRight", "ArrowLeft", "Home", "End"].includes(
                        event.key,
                      )
                    ) {
                      event.preventDefault();
                      const next =
                        event.key === "Home"
                          ? 0
                          : event.key === "End"
                            ? 6
                            : (index + (event.key === "ArrowRight" ? 1 : 6)) %
                              7;
                      setStage(next);
                      document.getElementById(`stage-${next}`)?.focus();
                    }
                  }}
                >
                  <span className="stage-number">0{index + 1}</span>
                  <Icon size={21} strokeWidth={1.5} />
                  <span>{name}</span>
                </button>
              );
            })}
          </div>
          <div
            className="process-preview"
            role="tabpanel"
            id="stage-panel"
            aria-labelledby={`stage-${stage}`}
          >
            <aside className="preview-aside">
              <div className="preview-project">
                <span className="project-dot" />
                <span>{c.sample}</span>
              </div>
              <div className="dataset-preview">
                <Database size={24} strokeWidth={1.5} />
                <span>{c.input}</span>
                <strong>customers.csv</strong>
                <div>
                  <span>2 000 {c.rows}</span>
                  <span>10 {c.columns}</span>
                </div>
              </div>
              <div className="preview-route">
                {c.stageNames.map((name, index) => (
                  <div
                    key={name}
                    className={index === stage ? "is-current" : ""}
                  >
                    <span>
                      {index < stage ? <Check size={12} /> : `0${index + 1}`}
                    </span>
                    {name}
                    {index === stage && <ChevronRight size={14} />}
                  </div>
                ))}
              </div>
              <p className="preview-disclaimer">{c.illustrative}</p>
            </aside>
            <div className="preview-content" key={stage}>
              <div className="preview-stage-icon">
                <StageIcon size={26} strokeWidth={1.5} />
              </div>
              <p className="eyebrow">0{stage + 1} / 07</p>
              <h3>{c.stageTitles[stage]}</h3>
              <p className="stage-description">{c.stageDescriptions[stage]}</p>
              <div className="stage-visual">
                {stage === 0 && (
                  <div className="analysis-checks">
                    {c.checks.map((text) => (
                      <div key={text}>
                        <Check size={16} />
                        <span>{text}</span>
                      </div>
                    ))}
                  </div>
                )}
                {stage === 1 && (
                  <div className="analysis-checks">
                    {c.plan.map((text, i) => (
                      <div key={text}>
                        <span className="plan-index">0{i + 1}</span>
                        <span>{text}</span>
                      </div>
                    ))}
                  </div>
                )}
                {(stage === 2 || stage === 3 || stage === 5) && (
                  <>
                    <div className="comparison-header">
                      <span>{stage === 5 ? c.improved : c.metric}</span>
                      <span>F1</span>
                    </div>
                    {[
                      { name: "Dummy", value: 0.34 },
                      { name: "Logistic Regression", value: 0.56 },
                      {
                        name: "Random Forest",
                        value: stage === 5 ? 0.62 : 0.59,
                      },
                    ].map((item, i) => (
                      <div className="model-comparison" key={item.name}>
                        <div>
                          <span>{item.name}</span>
                          <strong>{item.value.toFixed(2)}</strong>
                        </div>
                        <div className="model-bar">
                          <span
                            style={{
                              width: `${item.value * 100}%`,
                              background: i === 2 ? "#0071e3" : "#c7c7cc",
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </>
                )}
                {stage === 4 && (
                  <div className="analysis-checks">
                    {c.risk.map((text) => (
                      <div key={text}>
                        <ShieldCheck size={16} />
                        <span>{text}</span>
                      </div>
                    ))}
                  </div>
                )}
                {stage === 6 && (
                  <div className="artifact-list">
                    {[
                      { name: "model.joblib", icon: PackageCheck },
                      { name: "inference.py", icon: FileText },
                      { name: c.generated, icon: FileText },
                    ].map((item) => (
                      <div key={item.name}>
                        <item.icon size={18} />
                        <span>{item.name}</span>
                        <Download size={15} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="stage-output">
                <span>{c.output}</span>
                <strong>{c.outputs[stage]}</strong>
                <ArrowRight size={18} />
              </div>
            </div>
          </div>
        </section>
        <section id="features" className="features-section">
          <div className="section-heading">
            <h2>{c.featuresTitle}</h2>
            <p>{c.featuresIntro}</p>
          </div>
          <div className="feature-grid">
            {[Database, ChartNoAxesCombined, PackageCheck].map((Icon, i) => (
              <article key={i}>
                <span className="feature-index">0{i + 1}</span>
                <Icon size={32} strokeWidth={1.3} />
                <h3>{c.featureNames[i]}</h3>
                <p>{c.featureBody[i]}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="landing-cta">
          <p className="eyebrow">MLUTION</p>
          <h2>{c.ctaTitle}</h2>
          <p>{c.ctaBody}</p>
          <Link href="/projects/new" className="primary-pill">
            {c.start}
            <ArrowRight size={17} />
          </Link>
        </section>
      </main>
      <footer className="landing-footer">
        <Logo />
        <p>{c.footer}</p>
        <LanguageSwitcher />
      </footer>
    </div>
  );
}
