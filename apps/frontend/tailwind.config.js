/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        panel: "#111827",
        muted: "#94a3b8",
        border: "#1f2937",
        accent: "#22c55e",
      },
    },
  },
  plugins: [],
};
