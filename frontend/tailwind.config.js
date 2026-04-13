/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        node: {
          function: '#3b82f6',
          schema: '#a855f7',
          api: '#22c55e',
        },
        edge: {
          call: '#3b82f6',
          dataflow: '#f97316',
          incompatible: '#ef4444',
        },
      },
    },
  },
  plugins: [],
}
