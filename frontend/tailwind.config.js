/** @type {import('tailwindcss').Config} */
export default {
  content: [
    'index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#4F46E5',
          hover: '#4338CA',
          active: '#3730A3',
          light: '#EEF2FF',
          subtle: '#E0E7FF',
        },
      },
      fontFamily: {
        sans: ['var(--font-family)'],
        mono: ['var(--font-mono)'],
      },
      borderRadius: {
        sm: '4px',
        md: '6px',
        lg: '8px',
      },
    },
  },
  plugins: [],
}
