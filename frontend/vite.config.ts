import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Local development: the dev server proxies REST and WebSocket traffic to the
// FastAPI backend, so the browser (and phones on the same Wi-Fi, thanks to
// `host: true`) only ever talk to one origin.
const backend = process.env.MIZEMI_DEV_BACKEND ?? 'http://127.0.0.1:8000'
const proxy = {
  '/api': { target: backend, changeOrigin: true },
  '/ws': { target: backend.replace(/^http/, 'ws'), ws: true, changeOrigin: true },
}

export default defineConfig({
  plugins: [react()],
  server: { host: true, proxy },
  preview: { host: true, proxy },
  test: {
    environment: 'jsdom',
    // Node 26's native localStorage must not shadow jsdom's browser storage.
    execArgv: ['--no-experimental-webstorage'],
    setupFiles: './src/setupTests.ts',
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
  },
})
