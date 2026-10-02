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
        background: "#09090B",
        card: "#121218",
        brand: {
          DEFAULT: "#8B5CF6",
          foreground: "#FFFFFF",
        },
        accent: {
          DEFAULT: "#22D3EE",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 8px 30px rgba(0, 0, 0, 0.35)",
        glow: "0 0 40px rgba(139, 92, 246, 0.25)",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(139, 92, 246, 0.45)" },
          "50%": { boxShadow: "0 0 24px 4px rgba(139, 92, 246, 0.2)" },
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
