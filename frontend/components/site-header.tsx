import Link from "next/link";
import { Plus, LayoutDashboard } from "lucide-react";
import { Logo } from "@/components/logo";
import { buttonVariants } from "@/components/ui/button";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Logo />
          <nav className="hidden items-center gap-1 sm:flex">
            <Link
              href="/dashboard"
              className={buttonVariants({ variant: "ghost", size: "sm" })}
            >
              <LayoutDashboard className="h-3.5 w-3.5" />
              Dashboard
            </Link>
          </nav>
        </div>
        <Link href="/projects/new" className={buttonVariants({ size: "sm" })}>
          <Plus className="h-4 w-4" />
          New project
        </Link>
      </div>
    </header>
  );
}
