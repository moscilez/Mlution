"use client";
import { useI18n } from "@/lib/i18n";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { authenticate, demoLogin, createProject, request } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Logo } from "@/components/logo";
import { LanguageSwitcher } from "@/components/language-switcher";

export function AuthForm({
  mode,
}: {
  mode: "login" | "register" | "forgot-password" | "reset-password";
}) {
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [resetUrl, setResetUrl] = useState("");
  const router = useRouter();
  const cache = useQueryClient();
  const titles = {
    login: "Welcome to your ML workspace",
    register: "Build your next ML solution",
    "forgot-password": "Recover your account",
    "reset-password": "Choose a new password",
  };
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      if (mode === "login" || mode === "register") {
        const user = await authenticate(mode, email, password);
        cache.clear();
        cache.setQueryData(["me"], user);
        const next = new URLSearchParams(window.location.search).get("next");
        router.push(
          next?.startsWith("/") && !next.startsWith("//") ? next : "/dashboard",
        );
      } else if (mode === "forgot-password") {
        const result = await request<{ message: string; reset_url?: string }>(
          "/api/auth/forgot-password",
          { method: "POST", body: JSON.stringify({ email }) },
        );
        setMessage(result.message);
        setResetUrl(result.reset_url ?? "");
      } else {
        await request("/api/auth/reset-password", {
          method: "POST",
          body: JSON.stringify({
            password,
            token: new URLSearchParams(window.location.search).get("token"),
          }),
        });
        router.push("/login");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Please try again");
    } finally {
      setBusy(false);
    }
  }
  async function demo() {
    setBusy(true);
    setMessage("");
    try {
      const user = await demoLogin();
      cache.clear();
      cache.setQueryData(["me"], user);
      const project = await createProject({
        name: t("Telco Churn Demo"),
        description: t(
          "Predict customer churn. Compare a baseline and an improved model.",
        ),
        use_demo_dataset: true,
        target_column: "churn",
        primary_metric: "f1",
      });
      router.push(`/projects/${project.id}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Demo unavailable");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="glow-violet flex min-h-[85vh] items-center justify-center px-4 py-12">
      <div className="w-full max-w-md rounded-2xl border border-blue-400/20 bg-card p-8 shadow-soft">
        <div className="flex items-center justify-between gap-4">
          <Logo />
          <LanguageSwitcher />
        </div>
        <h1 className="mt-8 text-2xl font-semibold">{t(titles[mode])}</h1>
        <p className="mt-2 text-sm text-zinc-600">
          {t("From idea to ML solution. Your data, your experiments.")}
        </p>
        <form onSubmit={submit} className="mt-8 space-y-5">
          {mode !== "reset-password" && (
            <label className="block text-sm">
              {t("Email")}
              <Input
                className="mt-2"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
          )}
          {mode !== "forgot-password" && (
            <label className="block text-sm">
              {t("Password")}
              <Input
                className="mt-2"
                type="password"
                aria-label={t("Password")}
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                minLength={10}
                maxLength={128}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <span className="mt-2 block text-xs text-zinc-500">
                {t("At least 10 characters.")}
              </span>
            </label>
          )}
          {message && (
            <p role="alert" className="break-words text-sm text-blue-700">
              {t(message)}
            </p>
          )}
          {resetUrl && (
            <Link
              className="block text-sm text-blue-300 underline"
              href={resetUrl}
            >
              {t("Open local development reset link")}
            </Link>
          )}
          <Button disabled={busy} className="w-full" type="submit">
            {t(
              busy
                ? "Please wait…"
                : mode === "login"
                  ? "Sign in"
                  : mode === "register"
                    ? "Create account"
                    : "Continue",
            )}
          </Button>
        </form>
        {(mode === "login" || mode === "register") && (
          <Button
            className="mt-3 w-full"
            variant="outline"
            onClick={demo}
            disabled={busy}
          >
            {t("Continue with demo account")}
          </Button>
        )}
        <div className="mt-6 flex flex-wrap justify-between gap-3 text-sm text-zinc-600">
          <Link href={mode === "register" ? "/login" : "/register"}>
            {t(mode === "register" ? "Sign in" : "Create account")}
          </Link>
          <Link href="/forgot-password">{t("Forgot password?")}</Link>
        </div>
      </div>
    </main>
  );
}
