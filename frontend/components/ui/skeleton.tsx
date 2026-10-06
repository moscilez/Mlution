import { cn } from "@/lib/utils";

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-xl bg-zinc-100 border border-zinc-200",
        className,
      )}
      {...props}
    />
  );
}

export { Skeleton };
