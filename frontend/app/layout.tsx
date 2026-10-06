import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Mlution — От данных к решению",
  description:
    "Mlution анализирует данные, обучает и сравнивает модели машинного обучения. От CSV до модели, понятного отчёта и предсказаний.",
  icons: { icon: "/mlution-mark.png" },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body className="min-h-screen bg-background font-sans text-zinc-900 antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
