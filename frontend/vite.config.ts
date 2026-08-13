import { defineConfig } from 'vitest/config'
import { loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    // Relative /query calls use this proxy in development. A configured
    // VITE_API_BASE_URL bypasses it and requires the backend's CORS support.
    server: { proxy: { '/query': { target: env.VITE_DEV_API_PROXY_TARGET || 'http://localhost:8000', changeOrigin: true } } },
    test: {
      environment: 'jsdom',
    },
  }
})
