import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          "flex h-10 w-full appearance-none rounded-xl border border-white/10 bg-white/5 px-3 py-2 pr-9 text-sm text-zinc-100 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:border-brand/50 disabled:cursor-not-allowed disabled:opacity-50 [&>option]:bg-zinc-900",
          className
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
    </div>
  )
);
Select.displayName = "Select";

export { Select };
