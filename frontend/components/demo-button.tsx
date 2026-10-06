"use client";
import { useI18n } from "@/lib/i18n";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createProject, getMe, demoLogin } from "@/lib/api";
import { Button } from "@/components/ui/button";

export function DemoButton() {
  const { t } = useI18n();
  const router = useRouter();
  const cache = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function openDemo() {
    setBusy(true);
    setError("");
    try {
      let user;
      try {
        user = await getMe();
      } catch {
        user = await demoLogin();
      }
      cache.setQueryData(["me"], user);
      const project = await createProject({
        name: t("Telco Churn Demo"),
        description: t(
          "Predict customer churn from subscription and usage data.",
        ),
        use_demo_dataset: true,
        target_column: "churn",
        primary_metric: "f1",
      });
      router.push(`/projects/${project.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Demo unavailable");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div>
      <Button size="lg" variant="outline" disabled={busy} onClick={openDemo}>
        {t(busy ? "Preparing demo…" : "Try demo")}
      </Button>
      {error && (
        <p role="alert" className="mt-2 max-w-sm text-sm text-red-700">
          {t(error)}
        </p>
      )}
    </div>
  );
}
