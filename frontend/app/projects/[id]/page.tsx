"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Download,
  FileCode,
  Play,
  Sparkles,
} from "lucide-react";
import {
  codeDownloadUrl,
  getEvents,
  getExperiments,
  getProfile,
  getProject,
  getReport,
  getStatus,
  modelDownloadUrl,
} from "@/lib/api";
import { useLiveProject } from "@/lib/use-live-project";
import { SiteHeader } from "@/components/site-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ErrorState } from "@/components/error-state";
import { EmptyState } from "@/components/empty-state";
import { AgentChat } from "@/components/workspace/agent-chat";
import { PipelineTimeline } from "@/components/workspace/pipeline-timeline";
import { DataProfileTab } from "@/components/workspace/data-profile-tab";
import { ExperimentsTab } from "@/components/workspace/experiments-tab";
import { LogsTab } from "@/components/workspace/logs-tab";
import { ReportTab } from "@/components/workspace/report-tab";

export default function WorkspacePage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const live = useLiveProject(projectId);

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
    refetchInterval: live.refetchInterval,
  });
  const statusQuery = useQuery({
    queryKey: ["status", projectId],
    queryFn: () => getStatus(projectId),
    refetchInterval: live.refetchInterval,
  });
  const eventsQuery = useQuery({
    queryKey: ["events", projectId],
    queryFn: () => getEvents(projectId),
    refetchInterval: live.refetchInterval,
  });
  const profileQuery = useQuery({
    queryKey: ["profile", projectId],
    queryFn: () => getProfile(projectId),
    retry: false,
    refetchInterval: live.refetchInterval,
  });
  const experimentsQuery = useQuery({
    queryKey: ["experiments", projectId],
    queryFn: () => getExperiments(projectId),
    refetchInterval: live.refetchInterval,
  });
  const reportQuery = useQuery({
    queryKey: ["report", projectId],
    queryFn: () => getReport(projectId),
    retry: false,
    enabled: projectQuery.data?.status === "completed",
  });

  const project = projectQuery.data;
  const completed = project?.status === "completed";

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="mx-auto max-w-[1500px] space-y-6 px-4 py-8 sm:px-6">
        {projectQuery.isLoading ? (
          <Skeleton className="h-20" />
        ) : projectQuery.isError || !project ? (
          <ErrorState
            title="Project not found"
            message="It may have been deleted, or the backend is unreachable."
            onRetry={() => projectQuery.refetch()}
          />
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <Link href="/dashboard">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="h-4 w-4" /> Dashboard
                </Button>
              </Link>
              <h1 className="text-xl font-semibold text-zinc-100">{project.name}</h1>
              <StatusBadge status={project.status} />
              <div className="ml-auto flex flex-wrap items-center gap-2">
                <a href={modelDownloadUrl(projectId)} aria-disabled={!completed}
                   className={completed ? "" : "pointer-events-none opacity-40"}>
                  <Button variant="outline" size="sm" disabled={!completed}>
                    <Download className="h-4 w-4" /> Model
                  </Button>
                </a>
                <a href={codeDownloadUrl(projectId)} aria-disabled={!completed}
                   className={completed ? "" : "pointer-events-none opacity-40"}>
                  <Button variant="outline" size="sm" disabled={!completed}>
                    <FileCode className="h-4 w-4" /> Code
                  </Button>
                </a>
                <Link href={`/projects/${projectId}/results`}
                      className={completed ? "" : "pointer-events-none opacity-40"}>
                  <Button variant="secondary" size="sm" disabled={!completed}>
                    <BarChart3 className="h-4 w-4" /> Results
                  </Button>
                </Link>
                <Link href={`/projects/${projectId}/predict`}
                      className={completed ? "" : "pointer-events-none opacity-40"}>
                  <Button size="sm" disabled={!completed}>
                    <Play className="h-4 w-4" /> Playground
                  </Button>
                </Link>
              </div>
            </div>

            {project.status === "failed" && project.error ? (
              <div className="flex items-start gap-3 rounded-2xl border border-red-400/30 bg-red-500/10 p-4">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-300" />
                <div>
                  <p className="text-sm font-medium text-red-200">Run failed</p>
                  <p className="mt-0.5 font-mono text-xs text-red-300/80">{project.error}</p>
                </div>
              </div>
            ) : null}

            <div className="grid gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">
              <Card className="flex h-[calc(100vh-11rem)] min-h-[480px] flex-col overflow-hidden lg:sticky lg:top-6">
                <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
                  <Sparkles className="h-4 w-4 text-brand" />
                  <p className="text-sm font-medium text-zinc-100">Agent</p>
                  {live.fallback ? (
                    <span className="ml-auto text-[10px] uppercase tracking-wide text-zinc-500">
                      polling
                    </span>
                  ) : null}
                </div>
                <AgentChat
                  projectId={projectId}
                  events={eventsQuery.data ?? []}
                  className="min-h-0 flex-1"
                />
              </Card>

              <div className="min-w-0 space-y-6">
                <Card className="p-4">
                  <PipelineTimeline status={statusQuery.data} />
                </Card>

                <Tabs defaultValue="profile">
                  <TabsList>
                    <TabsTrigger value="profile">Data Profile</TabsTrigger>
                    <TabsTrigger value="experiments">Experiments</TabsTrigger>
                    <TabsTrigger value="logs">Logs</TabsTrigger>
                    <TabsTrigger value="report">Report</TabsTrigger>
                  </TabsList>

                  <TabsContent value="profile">
                    {profileQuery.isLoading ? (
                      <Skeleton className="h-72" />
                    ) : profileQuery.isError || !profileQuery.data ? (
                      <EmptyState
                        title="No dataset profile"
                        description="Attach a CSV from the New Project page to see the automatic data profile."
                      />
                    ) : (
                      <DataProfileTab profile={profileQuery.data} />
                    )}
                  </TabsContent>

                  <TabsContent value="experiments">
                    {experimentsQuery.isLoading ? (
                      <Skeleton className="h-72" />
                    ) : (
                      <ExperimentsTab
                        experiments={experimentsQuery.data ?? []}
                        bestExperimentId={project.best_experiment_id}
                      />
                    )}
                  </TabsContent>

                  <TabsContent value="logs">
                    <LogsTab events={eventsQuery.data ?? []} />
                  </TabsContent>

                  <TabsContent value="report">
                    {reportQuery.isLoading ? (
                      <Skeleton className="h-72" />
                    ) : !reportQuery.data ? (
                      <EmptyState
                        title="Report not ready"
                        description="The final report appears here once the pipeline reaches the Finalize stage."
                      />
                    ) : (
                      <ReportTab report={reportQuery.data} />
                    )}
                  </TabsContent>
                </Tabs>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
