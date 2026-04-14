/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        outfit: ['Outfit', 'sans-serif'],
        manrope: ['Manrope', 'sans-serif'],
      },
      colors: {
        surface: {
          base: '#0A0A0A',
          card: '#141415',
          elevated: '#1C1D21',
          hover: '#22242B',
        },
        accent: {
          DEFAULT: '#10B981',
          hover: '#059669',
        },
      },
    },
  },
  plugins: [],
}
