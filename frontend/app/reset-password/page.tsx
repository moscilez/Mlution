"use client";
import { useI18n } from "@/lib/i18n";
import { AuthForm } from "@/components/auth-form";
export default function Page() {
  const { t } = useI18n();
  return <AuthForm mode="reset-password" />;
}
