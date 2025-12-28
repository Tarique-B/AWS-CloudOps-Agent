/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'stealth-bg': '#0a0a0a',
        'stealth-surface': '#121212',
        'stealth-card': '#1a1a1a',
        'neon-primary': '#00ff9d', // Popy green
        'neon-secondary': '#bd00ff', // Popy purple
        'neon-accent': '#00eaff', // Popy blue
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}

