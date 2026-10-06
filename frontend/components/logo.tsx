import Link from "next/link";
import { cn } from "@/lib/utils";
import Image from "next/image";

export function LogoMark({ className }: { className?: string }) {
  return (
    <Image
      src="/mlution-mark.png"
      alt=""
      width={40}
      height={40}
      className={cn("h-9 w-9 object-contain", className)}
      aria-hidden="true"
    />
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      className={cn(
        "flex items-center gap-2.5 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand",
        className,
      )}
    >
      <LogoMark />
      <span className="text-[21px] font-semibold tracking-[-0.06em] text-zinc-900">
        Mlution
      </span>
    </Link>
  );
}
