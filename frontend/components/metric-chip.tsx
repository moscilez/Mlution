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
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium",
        highlight
          ? "border-brand/40 bg-brand/15 text-violet-200"
          : "border-white/10 bg-white/5 text-zinc-300",
        className
      )}
    >
      <span className="uppercase tracking-wide text-[10px] text-zinc-500">{name}</span>
      <span className={cn("font-semibold tabular-nums", highlight && "text-violet-100")}>
        {formatNumber(value)}
      </span>
    </span>
  );
}
