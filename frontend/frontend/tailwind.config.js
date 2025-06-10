/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        // This makes the 'Inter' font available via the `font-sans` utility class
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}