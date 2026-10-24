"use client";
import { useI18n } from "@/lib/i18n";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMe } from "@/lib/api";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  const path = usePathname();
  const router = useRouter();
  const privatePage =
    path.startsWith("/dashboard") ||
    path.startsWith("/projects") ||
    path.startsWith("/competition") ||
    path.startsWith("/settings");
  const user = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    enabled: privatePage,
    retry: false,
  });
  useEffect(() => {
    if (privatePage && user.isError)
      router.replace(`/login?next=${encodeURIComponent(path)}`);
  }, [privatePage, user.isError, router, path]);
  if (privatePage && !user.data)
    return (
      <div
        role="status"
        className="mx-auto max-w-7xl animate-pulse px-6 py-20 text-zinc-600"
      >
        {t("Opening your workspace…")}
      </div>
    );
  return children;
}
