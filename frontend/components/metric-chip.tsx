"use client";
import { useI18n } from "@/lib/i18n";
import { cn, formatNumber } from "@/lib/utils";

export function MetricChip({
  name,
  value,
  className,
  highlight = false,
}: {
  name: string;
  value: number | null | undefined;
  className?: string;
  highlight?: boolean;
}) {
  const { t } = useI18n();
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium",
        highlight
          ? "border-brand/40 bg-brand/15 text-blue-700"
          : "border-zinc-200 bg-zinc-100 text-zinc-700",
        className,
      )}
    >
      <span className="uppercase tracking-wide text-[10px] text-zinc-500">
        {t(name)}
      </span>
      <span
        className={cn(
          "font-semibold tabular-nums",
          highlight && "text-blue-700",
        )}
      >
        {t(formatNumber(value))}
      </span>
    </span>
  );
}
