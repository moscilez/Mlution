import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#F5F5F7",
        card: "#FFFFFF",
        brand: {
          DEFAULT: "#0071E3",
          foreground: "#FFFFFF",
        },
        accent: {
          DEFAULT: "#0066CC",
        },
      },
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Arial", "sans-serif"],
      },
      boxShadow: {
        soft: "0 12px 48px rgba(29, 29, 31, 0.06)",
        glow: "0 4px 16px rgba(0, 113, 227, 0.08)",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(0, 113, 227, 0.2)" },
          "50%": { boxShadow: "0 0 0 5px rgba(0, 113, 227, 0.08)" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "fade-up": "fade-up 0.4s ease-out both",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
