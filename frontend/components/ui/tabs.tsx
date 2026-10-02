"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface TabsContextValue {
  value: string;
  setValue: (value: string) => void;
}

const TabsContext = React.createContext<TabsContextValue | null>(null);

function useTabs() {
  const ctx = React.useContext(TabsContext);
  if (!ctx) throw new Error("Tabs components must be used inside <Tabs>");
  return ctx;
}

interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultValue: string;
  value?: string;
  onValueChange?: (value: string) => void;
}

function Tabs({ defaultValue, value, onValueChange, className, children, ...props }: TabsProps) {
  const [internal, setInternal] = React.useState(defaultValue);
  const current = value ?? internal;
  const setValue = React.useCallback(
    (v: string) => {
      setInternal(v);
      onValueChange?.(v);
    },
    [onValueChange]
  );
  return (
    <TabsContext.Provider value={{ value: current, setValue }}>
      <div className={cn("flex flex-col gap-4", className)} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

const TabsList = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      role="tablist"
      className={cn(
        "inline-flex w-fit max-w-full flex-wrap items-center gap-1 rounded-xl border border-white/10 bg-white/5 p-1",
        className
      )}
      {...props}
    />
  )
);
TabsList.displayName = "TabsList";

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}

const TabsTrigger = React.forwardRef<HTMLButtonElement, TabsTriggerProps>(
  ({ className, value, ...props }, ref) => {
    const { value: current, setValue } = useTabs();
    const active = current === value;
    return (
      <button
        ref={ref}
        type="button"
        role="tab"
        aria-selected={active}
        onClick={() => setValue(value)}
        className={cn(
          "inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:pointer-events-none disabled:opacity-50",
          active
            ? "bg-brand text-white shadow-glow"
            : "text-zinc-400 hover:text-zinc-100 hover:bg-white/5",
          className
        )}
        {...props}
      />
    );
  }
);
TabsTrigger.displayName = "TabsTrigger";

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

const TabsContent = React.forwardRef<HTMLDivElement, TabsContentProps>(
  ({ className, value, ...props }, ref) => {
    const { value: current } = useTabs();
    if (current !== value) return null;
    return (
      <div
        ref={ref}
        role="tabpanel"
        className={cn("animate-fade-up focus-visible:outline-none", className)}
        {...props}
      />
    );
  }
);
TabsContent.displayName = "TabsContent";

export { Tabs, TabsList, TabsTrigger, TabsContent };
