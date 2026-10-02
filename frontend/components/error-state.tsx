"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
  className,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-2xl border border-red-400/20 bg-red-400/5 px-6 py-12 text-center",
        className
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-red-400/10 border border-red-400/20">
        <AlertTriangle className="h-6 w-6 text-red-400" />
      </div>
      <div className="space-y-1">
        <p className="font-semibold text-zinc-100">{title}</p>
        {message ? <p className="max-w-md text-sm text-zinc-400">{message}</p> : null}
      </div>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCcw className="h-3.5 w-3.5" />
          Retry
        </Button>
      ) : null}
    </div>
  );
}
