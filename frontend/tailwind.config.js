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
        'neon-primary': '#a855f7', // Purple from agentcore logo
        'neon-secondary': '#ec4899', // Pink from agentcore logo
        'neon-accent': '#fb923c', // Orange from agentcore logo
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

