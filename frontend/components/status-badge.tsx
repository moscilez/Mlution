import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ExperimentStatus, ProjectStatus } from "@/lib/types";

const statusConfig: Record<
  string,
  { label: string; className: string; dot: string; pulse?: boolean }
> = {
  created: {
    label: "Created",
    className: "border-zinc-400/30 bg-zinc-400/10 text-zinc-300",
    dot: "bg-zinc-400",
  },
  running: {
    label: "Running",
    className: "border-cyan-400/30 bg-cyan-400/10 text-cyan-300",
    dot: "bg-cyan-400",
    pulse: true,
  },
  completed: {
    label: "Completed",
    className: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
    dot: "bg-emerald-400",
  },
  failed: {
    label: "Failed",
    className: "border-red-400/30 bg-red-400/10 text-red-300",
    dot: "bg-red-400",
  },
  pending: {
    label: "Pending",
    className: "border-zinc-400/30 bg-zinc-400/10 text-zinc-400",
    dot: "bg-zinc-500",
  },
};

export function StatusBadge({
  status,
  className,
}: {
  status: ProjectStatus | ExperimentStatus | string;
  className?: string;
}) {
  const config = statusConfig[status] ?? statusConfig.created;
  return (
    <Badge className={cn("capitalize", config.className, className)}>
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          config.dot,
          config.pulse && "animate-ping"
        )}
      />
      {config.label}
    </Badge>
  );
}
