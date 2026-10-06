"use client";
import { useI18n } from "@/lib/i18n";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { request } from "@/lib/api";
import { SiteHeader } from "@/components/site-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
  const { t } = useI18n();
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  const cache = useQueryClient();
  async function mutate(path: string, init: RequestInit) {
    setBusy(true);
    setMessage("");
    try {
      await request(path, init);
      cache.clear();
      router.replace("/login");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-xl space-y-6 px-4 py-12">
        <h1 className="text-2xl font-semibold">{t("Account settings")}</h1>
        <form
          className="space-y-4 rounded-xl border border-zinc-200 bg-card p-6"
          onSubmit={(e) => {
            e.preventDefault();
            void mutate("/api/auth/change-password", {
              method: "POST",
              body: JSON.stringify({
                current_password: current,
                new_password: password,
              }),
            });
          }}
        >
          <label className="block text-sm">
            {t("Current password")}
            <Input
              type="password"
              autoComplete="current-password"
              required
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            {t("New password")}
            <Input
              type="password"
              autoComplete="new-password"
              required
              minLength={10}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <Button type="submit" disabled={busy}>
            {t("Change password and sign out")}
          </Button>
        </form>
        {message && (
          <p role="alert" className="text-sm text-red-700">
            {t(message)}
          </p>
        )}
        <Button
          disabled={busy}
          variant="outline"
          onClick={() => {
            if (
              window.confirm(
                t("Delete your account and all projects permanently?"),
              )
            )
              void mutate("/api/auth/account", { method: "DELETE" });
          }}
        >
          {t("Delete account")}
        </Button>
      </main>
    </>
  );
}
