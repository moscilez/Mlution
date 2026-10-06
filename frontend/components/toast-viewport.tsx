"use client";
import { useI18n } from "@/lib/i18n";
import { useEffect, useState } from "react";

export function ToastViewport() {
  const { t } = useI18n();
  const [toast, setToast] = useState<{
    message: string;
    error?: boolean;
  } | null>(null);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const receive = (event: Event) => {
      setToast(
        (event as CustomEvent<{ message: string; error?: boolean }>).detail,
      );
      clearTimeout(timer);
      timer = setTimeout(() => setToast(null), 6000);
    };
    window.addEventListener("mlution:toast", receive);
    return () => {
      window.removeEventListener("mlution:toast", receive);
      clearTimeout(timer);
    };
  }, []);
  if (!toast) return null;
  return (
    <div
      role={toast.error ? "alert" : "status"}
      className={`fixed bottom-5 right-5 z-[70] flex max-w-[calc(100vw-2.5rem)] items-start gap-4 rounded-xl border bg-card px-5 py-4 text-sm shadow-soft ${toast.error ? "border-red-400/40 text-red-700" : "border-cyan-400/40 text-blue-700"}`}
    >
      <span>{t(toast.message)}</span>
      <button
        onClick={() => setToast(null)}
        aria-label={t("Dismiss notification")}
      >
        {t("×")}
      </button>
    </div>
  );
}
