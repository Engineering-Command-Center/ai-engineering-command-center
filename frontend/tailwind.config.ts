import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f4ff",
          100: "#e0e9ff",
          200: "#c0d3ff",
          300: "#93b4ff",
          400: "#6691ff",
          500: "#4f6ef7",
          600: "#3a52d4",
          700: "#2d3fa8",
          800: "#243080",
          900: "#1a237e",
        },
      },
      typography: {
        DEFAULT: {
          css: {
            maxWidth: "none",
            color: "inherit",
            a: { color: "inherit" },
            strong: { color: "inherit" },
            code: { color: "inherit" },
          },
        },
      },
      keyframes: {
        "fade-in": { from: { opacity: "0", transform: "translateY(4px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        "pulse-dot": { "0%, 80%, 100%": { opacity: "0.3" }, "40%": { opacity: "1" } },
      },
      animation: {
        "fade-in": "fade-in 0.18s ease-out",
        "pulse-dot": "pulse-dot 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
