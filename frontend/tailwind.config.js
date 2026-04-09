/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        estate: {
          50: "#f4f7f1",
          100: "#dbe7d4",
          600: "#2f5f43",
          800: "#1d3c2a",
          900: "#12261a"
        }
      }
    },
  },
  plugins: [],
};
