"use client";
import { Globe2 } from "lucide-react";
import { useI18n } from "@/lib/i18n";

export function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();
  return (
    <div
      className="language-switcher"
      role="group"
      aria-label={locale === "ru" ? "Язык сайта" : "Website language"}
    >
      <Globe2 size={14} aria-hidden="true" />
      <button
        type="button"
        aria-label="Русский"
        aria-pressed={locale === "ru"}
        onClick={() => setLocale("ru")}
      >
        RU
      </button>
      <span aria-hidden="true">/</span>
      <button
        type="button"
        aria-label="English"
        aria-pressed={locale === "en"}
        onClick={() => setLocale("en")}
      >
        EN
      </button>
    </div>
  );
}
