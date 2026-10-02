import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-white/10 bg-card/50 px-6 py-14 text-center",
        className
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand/10 border border-brand/20">
        <Icon className="h-6 w-6 text-brand" />
      </div>
      <div className="space-y-1">
        <p className="font-semibold text-zinc-100">{title}</p>
        {description ? (
          <p className="max-w-sm text-sm text-zinc-400">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}
