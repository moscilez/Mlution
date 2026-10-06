"use client";
import { useI18n } from "@/lib/i18n";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cancelRun, getRuns, runProject } from "@/lib/api";
import type { Project } from "@/lib/types";
import { Button } from "@/components/ui/button";

export function RunControls({ project }: { project: Project }) {
  const { t } = useI18n();
  const cache = useQueryClient();
  const [message, setMessage] = useState("");
  const active = project.status === "queued" || project.status === "running";
  const runs = useQuery({
    queryKey: ["runs", project.id],
    queryFn: () => getRuns(project.id),
    refetchInterval: active ? 2500 : false,
  });
  const action = useMutation({
    mutationFn: async () => {
      if (active) {
        const run = runs.data?.find(
          (run) => run.status === "queued" || run.status === "running",
        );
        if (!run) throw new Error("Run status is updating. Please retry.");
        await cancelRun(project.id, run.id);
        setMessage(
          "Cancellation requested. The current model fit may need to finish.",
        );
      } else {
        await runProject(project.id, {
          target_column: project.target_column,
          primary_metric: project.primary_metric,
          business_priority: null,
          time_budget_seconds: 180,
          max_experiments: 4,
        });
        setMessage("Run queued. Live updates will appear below.");
      }
    },
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["project", project.id] });
      void cache.invalidateQueries({ queryKey: ["runs", project.id] });
    },
    onError: (e) =>
      setMessage(e instanceof Error ? e.message : "Run could not start"),
  });
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button
        disabled={action.isPending || !project.dataset_name}
        variant={active ? "outline" : "default"}
        onClick={() => action.mutate()}
      >
        {t(
          action.isPending
            ? "Please wait…"
            : active
              ? "Cancel run"
              : project.status === "created"
                ? "Run pipeline"
                : "Run again",
        )}
      </Button>
      {message && (
        <span role="status" className="max-w-md text-xs text-blue-700">
          {t(message)}
        </span>
      )}
    </div>
  );
}
