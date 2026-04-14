import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/project': 'http://localhost:8002',
      '/session': 'http://localhost:8002',
      '/operation': 'http://localhost:8002',
      '/proxy': 'http://localhost:8002',
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/tests/setup.ts',
  },
})
