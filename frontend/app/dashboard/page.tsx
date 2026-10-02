"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Plus, FolderOpen, Cpu } from "lucide-react";
import { listProjects } from "@/lib/api";
import { timeAgo } from "@/lib/utils";
import { TASK_TYPE_LABELS } from "@/lib/types";
import { SiteHeader } from "@/components/site-header";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { MetricChip } from "@/components/metric-chip";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

export default function DashboardPage() {
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  const projects = projectsQuery.data ?? [];

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto max-w-7xl space-y-8 px-4 py-10 sm:px-6">
        <PageHeader
          title="Projects"
          description="Every ML solution your agent has built, in one place."
          actions={
            <Link href="/projects/new">
              <span className="inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white shadow-glow transition-colors hover:bg-brand/90">
                <Plus className="h-4 w-4" />
                New project
              </span>
            </Link>
          }
        />

        {projectsQuery.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-44" />
            ))}
          </div>
        ) : projectsQuery.isError ? (
          <ErrorState
            title="Could not load projects"
            message={
              projectsQuery.error instanceof Error
                ? projectsQuery.error.message
                : "The API is unreachable. Make sure the backend is running."
            }
            onRetry={() => projectsQuery.refetch()}
          />
        ) : projects.length === 0 ? (
          <EmptyState
            icon={FolderOpen}
            title="No projects yet"
            description="Create your first ML project — describe the task, upload a CSV and let the agent do the rest."
            action={
              <Link href="/projects/new">
                <span className="inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white shadow-glow transition-colors hover:bg-brand/90">
                  <Plus className="h-4 w-4" />
                  Create project
                </span>
              </Link>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Link key={project.id} href={`/projects/${project.id}`} className="group">
                <Card className="h-full transition-all duration-300 group-hover:-translate-y-1 group-hover:border-brand/40 group-hover:shadow-glow">
                  <CardContent className="flex h-full flex-col gap-3 p-5">
                    <div className="flex items-start justify-between gap-2">
                      <p className="line-clamp-1 font-semibold text-zinc-100">{project.name}</p>
                      <StatusBadge status={project.status} />
                    </div>
                    <p className="line-clamp-2 min-h-[2.5rem] text-sm text-zinc-400">
                      {project.description}
                    </p>
                    <div className="mt-auto flex flex-wrap items-center gap-2 pt-2">
                      {project.task_type ? (
                        <Badge variant="secondary">
                          {TASK_TYPE_LABELS[project.task_type] ?? project.task_type}
                        </Badge>
                      ) : null}
                      {project.primary_metric ? (
                        <MetricChip
                          name={project.primary_metric}
                          value={project.best_metric_value}
                          highlight={project.status === "completed"}
                        />
                      ) : null}
                    </div>
                    <div className="flex items-center justify-between border-t border-white/5 pt-3 text-xs text-zinc-500">
                      <span className="flex items-center gap-1.5">
                        <Cpu className="h-3.5 w-3.5" />
                        {project.best_model_type ?? "No model yet"}
                      </span>
                      <span>updated {timeAgo(project.updated_at)}</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
