import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Warm ivory canvas
        ivory: {
          DEFAULT: "#FAF6F1",
          card: "#FFFFFF",
          head: "#FBF7F2",
          line: "#ECE4DA",
          line2: "#F3EDE5",
          hover: "#FCFAF7",
        },
        // Deep plum chrome
        plum: {
          dark: "#16111F",
          panel: "#1C1528",
          50:  "#faf5ff",
          100: "#f3e8ff",
          200: "#e9d5ff",
          300: "#d8b4fe",
          400: "#c084fc",
          500: "#a855f7",
          600: "#9333ea",
          700: "#7e22ce",
          800: "#6b21a8",
          900: "#581c87",
        },
        // Ink (text on ivory)
        ink: {
          DEFAULT: "#281F2E",
          soft: "#6E6675",
          faint: "#A89D94",
        },
        // Brand accent
        coral: {
          DEFAULT: "#E8334A",
          hover: "#D02740",
        },
        // Muted, elegant status colors (on ivory)
        verdict: {
          green: "#1E7A50",
          red: "#BE3247",
          amber: "#AE7317",
          violet: "#6B56A6",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        serif: ["var(--font-fraunces)", "Georgia", "serif"],
      },
      boxShadow: {
        soft: "0 1px 3px rgba(40,31,46,0.04)",
        lift: "0 10px 30px rgba(40,31,46,0.08)",
        coral: "0 8px 20px rgba(232,51,74,0.22)",
        panel: "0 30px 80px rgba(0,0,0,0.5)",
      },
      backgroundImage: {
        // Plum hero twilight: deep indigo -> plum -> warm mauve-rose
        twilight:
          "radial-gradient(120% 140% at 15% 110%, rgba(232,120,140,0.35) 0%, rgba(0,0,0,0) 45%), radial-gradient(90% 120% at 88% -10%, rgba(150,110,200,0.30) 0%, rgba(0,0,0,0) 50%), linear-gradient(150deg, #1B1130 0%, #34204E 38%, #5E3A60 72%, #87526A 100%)",
      },
    },
  },
  plugins: [],
};
export default config;
