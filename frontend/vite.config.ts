/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_TARGET || 'http://127.0.0.1:8000'
  return {
    plugins: [react(), tailwindcss()],
    server: { port: 5173, strictPort: true, proxy: { '/api': { target, changeOrigin: true } } },
    test: { environment: 'node', include: ['src/**/*.test.ts'] },
  }
})
