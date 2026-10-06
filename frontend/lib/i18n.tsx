"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import { ru } from "./messages/ru";
import { machineRu } from "./messages/machine-ru";

export type Locale = "ru" | "en";
const LocaleContext = createContext<{
  locale: Locale;
  setLocale: (locale: Locale) => void;
}>({ locale: "ru", setLocale: () => {} });

export function translate<T>(value: T, locale: Locale): T {
  if (locale === "en" || typeof value !== "string") return value;
  const key = value.trim().replace(/\s+/g, " ");
  const message = Object.prototype.hasOwnProperty.call(ru, key)
    ? ru[key]
    : undefined;
  if (typeof message === "string") return message as T;
  const machineMessage = machineRu(key);
  if (machineMessage) return machineMessage as T;
  const units = key.match(/^([\d,.\s—]+) (rows|columns)$/);
  if (units)
    return `${units[1]} ${units[2] === "rows" ? "строк" : "столбцов"}` as T;
  const ago = key.match(/^(\d+)(s|m|h|d) ago$/);
  if (ago)
    return `${ago[1]} ${({ s: "сек.", m: "мин.", h: "ч.", d: "дн." } as Record<string, string>)[ago[2]]} назад` as T;
  const duration = key.match(/^([\d.]+)(ms|s|m)$/);
  if (duration)
    return `${duration[1]} ${{ ms: "мс", s: "с", m: "мин" }[duration[2] as "ms" | "s" | "m"]}` as T;
  return value;
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setCurrentLocale] = useState<Locale>("ru");
  useEffect(() => {
    try {
      const saved = localStorage.getItem("mlution.locale");
      if (saved === "en" || saved === "ru") setCurrentLocale(saved);
      else if (document.cookie.includes("mlution_locale=en"))
        setCurrentLocale("en");
    } catch {
      if (document.cookie.includes("mlution_locale=en")) setCurrentLocale("en");
    }
  }, []);
  useEffect(() => {
    document.documentElement.lang = locale;
    document.title =
      locale === "ru"
        ? "Mlution — От данных к решению"
        : "Mlution — From data to decisions";
  }, [locale]);
  const setLocale = useCallback((next: Locale) => {
    setCurrentLocale(next);
    try {
      localStorage.setItem("mlution.locale", next);
    } catch {
      /* Language still works without persistence. */
    }
    document.cookie = `mlution_locale=${next}; Path=/; Max-Age=31536000; SameSite=Lax`;
  }, []);
  return (
    <LocaleContext.Provider value={{ locale, setLocale }}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(LocaleContext);
  return {
    ...context,
    t: <T,>(value: T): T => translate(value, context.locale),
  };
}
