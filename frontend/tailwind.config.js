/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        lavender: {
          50: '#faf7ff',
          100: '#f3eeff',
          200: '#e9e0ff',
          300: '#d7c7ff',
          400: '#bfa3ff',
          500: '#a375ff',
          600: '#8a48f7',
          700: '#7532e0',
          800: '#6127bc',
          900: '#502299',
          950: '#300f68',
        },
        brand: {
          primary: '#6366f1',     // Indigo 500
          hover: '#4f46e5',       // Indigo 600
          dark: '#312e81',        // Indigo 900
          purple: '#7c3aed',      // Violet 600
          soft: '#ede9fe',        // Violet 100
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(76, 29, 149, 0.05), 0 1px 2px -1px rgba(76, 29, 149, 0.05)',
        'card-hover': '0 4px 6px -1px rgba(76, 29, 149, 0.08), 0 2px 4px -2px rgba(76, 29, 149, 0.08)',
        'elevated': '0 10px 15px -3px rgba(76, 29, 149, 0.1), 0 4px 6px -4px rgba(76, 29, 149, 0.1)',
      }
    },
  },
  plugins: [],
}
