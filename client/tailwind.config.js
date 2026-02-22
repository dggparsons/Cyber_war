/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        pixel: ["'Press Start 2P'", "monospace"],
      },
      colors: {
        "warroom-blue": "#0f172a",
        "warroom-slate": "#1e293b",
        "warroom-cyan": "#38bdf8",
        "warroom-amber": "#fbbf24",
      },
    },
  },
  plugins: [],
}
