import Link from "next/link";
import {
  ArrowRight,
  ScanSearch,
  ClipboardList,
  Hammer,
  Gauge,
  MessageSquare,
  TrendingUp,
  Rocket,
  Database,
  Boxes,
  Trophy,
  FileText,
  RefreshCcw,
  Download,
  Sparkles,
} from "lucide-react";
import { Logo } from "@/components/logo";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const stages = [
  { name: "Analyze", icon: ScanSearch, description: "Profiles your CSV and detects the target" },
  { name: "Plan", icon: ClipboardList, description: "Chooses task type and metrics" },
  { name: "Baseline", icon: Hammer, description: "Trains a first safe model" },
  { name: "Evaluate", icon: Gauge, description: "Scores it on held-out data" },
  { name: "Critique", icon: MessageSquare, description: "Reviews errors and risks" },
  { name: "Improve", icon: TrendingUp, description: "Iterates with tuned models" },
  { name: "Finalize", icon: Rocket, description: "Packages model, code and report" },
];

const features = [
  {
    icon: Database,
    title: "Auto data profiling",
    description:
      "Column types, missing values, duplicates, class balance and leakage suspects are detected before any training starts.",
  },
  {
    icon: Boxes,
    title: "Safe model zoo",
    description:
      "A curated set of robust, well-understood model families — no fragile exotics, only algorithms that ship reliably.",
  },
  {
    icon: Trophy,
    title: "Experiment leaderboard",
    description:
      "Every run is tracked with hyperparameters, train and validation metrics, ranked best-first for full transparency.",
  },
  {
    icon: FileText,
    title: "Explainable reports",
    description:
      "Feature importances, confusion matrices and plain-language reasoning behind every modeling decision.",
  },
  {
    icon: RefreshCcw,
    title: "Improvement loop",
    description:
      "The agent critiques its own baseline, forms hypotheses and keeps the changes that measurably help.",
  },
  {
    icon: Download,
    title: "One-click export",
    description:
      "Download the trained model and ready-to-run Python inference code the moment the run finalizes.",
  },
];

export default function LandingPage() {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden">
      <div className="glow-violet pointer-events-none absolute inset-x-0 top-0 h-[560px]" />
      <div className="glow-cyan pointer-events-none absolute inset-x-0 top-[480px] h-[420px]" />

      {/* Nav */}
      <header className="relative z-10 mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <nav className="flex items-center gap-2">
          <Link href="/dashboard" className={buttonVariants({ variant: "ghost", size: "sm" })}>
            Dashboard
          </Link>
          <Link href="/projects/new" className={buttonVariants({ size: "sm" })}>
            Create project
          </Link>
        </nav>
      </header>

      <main className="relative z-10 flex-1">
        {/* Hero */}
        <section className="mx-auto flex max-w-4xl flex-col items-center px-4 pb-20 pt-16 text-center sm:pt-24">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-brand/30 bg-brand/10 px-4 py-1.5 text-xs font-medium text-violet-300">
            <Sparkles className="h-3.5 w-3.5" />
            Autonomous ML agent
          </div>
          <h1 className="text-balance text-4xl font-extrabold tracking-tight sm:text-6xl">
            From idea to <span className="text-gradient">ML solution</span>
          </h1>
          <p className="mt-6 max-w-2xl text-pretty text-base text-zinc-400 sm:text-lg">
            Describe your task, drop in a CSV, and let the Mlution agent profile your data,
            train and critique models, and hand you back a ranked leaderboard, an explainable
            report and exportable artifacts — no notebooks required.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <Link href="/projects/new" className={cn(buttonVariants({ size: "lg" }), "group")}>
              Create project
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link href="/dashboard" className={buttonVariants({ variant: "outline", size: "lg" })}>
              View dashboard
            </Link>
          </div>
        </section>

        {/* Workflow strip */}
        <section className="mx-auto max-w-7xl px-4 pb-24 sm:px-6">
          <h2 className="mb-10 text-center text-sm font-semibold uppercase tracking-[0.2em] text-zinc-500">
            One agent, seven deliberate stages
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
            {stages.map((stage, index) => (
              <div key={stage.name} className="group relative">
                {index < stages.length - 1 ? (
                  <div className="absolute left-full top-1/2 hidden h-px w-3 -translate-y-1/2 bg-gradient-to-r from-brand/50 to-transparent lg:block" />
                ) : null}
                <Card className="h-full transition-all duration-300 hover:-translate-y-1 hover:border-brand/40 hover:shadow-glow">
                  <CardContent className="flex h-full flex-col items-start gap-2 p-4">
                    <div className="flex w-full items-center justify-between">
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-brand/25 bg-brand/10 text-violet-300 transition-colors group-hover:border-brand/50 group-hover:text-violet-200">
                        <stage.icon className="h-[18px] w-[18px]" />
                      </div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-600">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-zinc-100">{stage.name}</p>
                    <p className="text-xs leading-relaxed text-zinc-500">{stage.description}</p>
                  </CardContent>
                </Card>
              </div>
            ))}
          </div>
        </section>

        {/* Features */}
        <section className="mx-auto max-w-7xl px-4 pb-24 sm:px-6">
          <div className="mb-12 text-center">
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
              Everything a data scientist would check, automated
            </h2>
            <p className="mx-auto mt-3 max-w-2xl text-sm text-zinc-400">
              Mlution is opinionated about rigor: it validates data, guards against leakage,
              compares candidates fairly and explains itself at every step.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <Card
                key={feature.title}
                className="group transition-all duration-300 hover:-translate-y-1 hover:border-brand/40"
              >
                <CardContent className="flex flex-col gap-3 p-6">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-accent transition-colors group-hover:border-accent/40">
                    <feature.icon className="h-5 w-5" />
                  </div>
                  <p className="font-semibold text-zinc-100">{feature.title}</p>
                  <p className="text-sm leading-relaxed text-zinc-400">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Bottom CTA */}
        <section className="mx-auto max-w-4xl px-4 pb-24 text-center sm:px-6">
          <Card className="relative overflow-hidden">
            <div className="glow-violet absolute inset-0" />
            <CardContent className="relative flex flex-col items-center gap-5 px-6 py-14">
              <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
                Your next model is one CSV away
              </h2>
              <p className="max-w-xl text-sm text-zinc-400">
                Spin up a project, point the agent at your dataset and watch the pipeline
                reason its way to a production-ready baseline.
              </p>
              <Link href="/projects/new" className={cn(buttonVariants({ size: "lg" }), "group")}>
                Create project
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </CardContent>
          </Card>
        </section>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/10">
        <div className="mx-auto flex h-16 max-w-7xl flex-wrap items-center justify-between gap-2 px-4 text-xs text-zinc-500 sm:px-6">
          <div className="flex items-center gap-2">
            <Logo />
          </div>
          <p>From idea to ML solution — autonomous, explainable, exportable.</p>
        </div>
      </footer>
    </div>
  );
}
