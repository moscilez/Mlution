import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "border-brand/40 bg-brand/15 text-blue-700",
        secondary: "border-zinc-200 bg-zinc-100 text-zinc-700",
        outline: "border-zinc-200 text-zinc-600",
        success: "border-emerald-400/30 bg-emerald-400/10 text-emerald-700",
        warning: "border-amber-400/30 bg-amber-400/10 text-amber-700",
        destructive: "border-red-400/30 bg-red-400/10 text-red-700",
        info: "border-cyan-400/30 bg-cyan-400/10 text-blue-700",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends
    React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
