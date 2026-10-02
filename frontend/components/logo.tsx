import Link from "next/link";
import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand to-accent text-sm font-black text-background shadow-glow",
        className
      )}
      aria-hidden
    >
      M
    </span>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      className={cn(
        "flex items-center gap-2.5 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand",
        className
      )}
    >
      <LogoMark />
      <span className="text-lg font-bold tracking-tight text-zinc-100">
        Mlution
      </span>
    </Link>
  );
}
