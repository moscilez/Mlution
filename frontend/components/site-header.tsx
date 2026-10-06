"use client";
import { useI18n } from "@/lib/i18n";
import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { signOut } from "@/lib/api";
import { Plus, LayoutDashboard, Settings, LogOut } from "lucide-react";
import { LanguageSwitcher } from "@/components/language-switcher";
import { Logo } from "@/components/logo";
import { buttonVariants } from "@/components/ui/button";

export function SiteHeader() {
  const { t } = useI18n();
  const [palette, setPalette] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const cache = useQueryClient();
  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key === "k") {
        event.preventDefault();
        setPalette((v) => !v);
      }
      if (event.key === "Escape") setPalette(false);
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);
  async function logout() {
    try {
      await signOut();
      cache.clear();
      router.replace("/login");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign out failed");
    }
  }
  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Logo />
          <nav className="hidden items-center gap-1 sm:flex">
            <Link
              href="/dashboard"
              className={buttonVariants({ variant: "ghost", size: "sm" })}
            >
              <LayoutDashboard className="h-3.5 w-3.5" />
              {t("Dashboard")}
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-2">
          <LanguageSwitcher />
          <button
            aria-label={t("Open command palette")}
            onClick={() => setPalette(true)}
            className="hidden rounded-lg border border-zinc-200 px-2 py-1 text-xs text-zinc-600 lg:block"
          >
            {t("⌘ K")}
          </button>
          <Link
            href="/settings"
            aria-label={t("Account")}
            className="flex min-h-8 min-w-8 items-center justify-center text-xs text-zinc-600"
          >
            <Settings className="h-4 w-4 sm:hidden" />
            <span className="hidden sm:inline">{t("Account")}</span>
          </Link>
          <button
            onClick={logout}
            aria-label={t("Sign out")}
            className="flex min-h-8 min-w-8 items-center justify-center text-xs text-zinc-600"
          >
            <LogOut className="h-4 w-4 sm:hidden" />
            <span className="hidden sm:inline">{t("Sign out")}</span>
          </button>
          <Link
            href="/projects/new"
            aria-label={t("New project")}
            className={buttonVariants({ size: "sm" })}
          >
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">{t("New project")}</span>
          </Link>
        </div>
      </div>
      {error && (
        <p role="alert" className="px-4 py-2 text-sm text-red-700">
          {t(error)}
        </p>
      )}
      {palette && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/30 px-4 pt-28"
          onClick={() => setPalette(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={t("Command palette")}
            className="w-full max-w-md rounded-xl border border-blue-400/30 bg-card p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              autoFocus
              onClick={() => setPalette(false)}
              className="mb-4 text-sm text-zinc-600"
            >
              {t("Close (Esc)")}
            </button>
            {[
              ["Dashboard", "/dashboard"],
              ["New project", "/projects/new"],
              ["Account settings", "/settings"],
            ].map(([label, href]) => (
              <Link
                key={href}
                href={href}
                onClick={() => setPalette(false)}
                className="block rounded-lg px-4 py-3 hover:bg-blue-500/20"
              >
                {t(label)}
              </Link>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}
