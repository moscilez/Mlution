import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Mlution — From idea to ML solution",
  description:
    "Mlution turns a task description and a CSV file into a trained, explained and exportable machine learning solution — automatically.",
  icons: { icon: "/mlution.svg" },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} min-h-screen bg-background font-sans text-zinc-100 antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
