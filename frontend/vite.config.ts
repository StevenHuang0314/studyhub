import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Requests to /api are proxied to the FastAPI server during development, so the
// browser only ever talks to one origin and CORS never comes up locally.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
