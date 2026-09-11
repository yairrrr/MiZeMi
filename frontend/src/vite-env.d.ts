/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_WS_BASE_URL?: string
  /** Public REST base URL, e.g. https://mizemi-api.onrender.com (empty = same origin). */
  readonly VITE_MIZEMI_API_BASE_URL?: string
  /** Public WebSocket base URL, e.g. wss://mizemi-api.onrender.com (derived when unset). */
  readonly VITE_MIZEMI_WS_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
