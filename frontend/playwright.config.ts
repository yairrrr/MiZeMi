import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 10_000 },
  workers: 1,
  fullyParallel: false,
  reporter: 'list',
  use: { actionTimeout: 10_000, baseURL: 'http://127.0.0.1:4173', headless: true, trace: 'off' },
  webServer: [
    {
      command: '../.venv/bin/python -m http.server 8770 --bind 127.0.0.1 --directory ../docs',
      url: 'http://127.0.0.1:8770',
      reuseExistingServer: false,
    },
    {
      command: '../.venv/bin/python -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8765 --ws-max-size 65536',
      url: 'http://127.0.0.1:8765/api/v1/health',
      reuseExistingServer: false,
      env: { MIZEMI_ENV: 'test', MIZEMI_DATABASE_URL: 'sqlite:///./.e2e.db', MIZEMI_CORS_ORIGINS: 'http://127.0.0.1:4173', MIZEMI_QUESTIONS_PER_GAME: '20', MIZEMI_QUESTION_TIME_LIMIT_SECONDS: '20' },
    },
    {
      command: 'npm run build && npm exec vite preview -- --host 127.0.0.1 --port 4173 --strictPort',
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: false,
      env: { MIZEMI_DEV_BACKEND: 'http://127.0.0.1:8765', VITE_API_BASE_URL: 'http://127.0.0.1:8765', VITE_WS_BASE_URL: 'ws://127.0.0.1:8765' },
    },
  ],
})
