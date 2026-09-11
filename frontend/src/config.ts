// Backend location (MASTER_SPEC.md §16). Only public URLs live here — Vite
// inlines every VITE_* variable into the shipped bundle, so never put a secret
// in one.

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

/** REST base URL; empty means "same origin" (the Vite dev proxy locally). */
export function getApiBaseUrl(): string {
  return stripTrailingSlash(import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_MIZEMI_API_BASE_URL ?? '')
}

/**
 * WebSocket base URL. Explicit ``VITE_MIZEMI_WS_BASE_URL`` wins; otherwise it
 * is derived from the API base (http→ws, https→wss), and finally from the
 * page's own origin so the dev proxy works from phones on the same network.
 */
export function getWebSocketBaseUrl(): string {
  const explicit = import.meta.env.VITE_WS_BASE_URL ?? import.meta.env.VITE_MIZEMI_WS_BASE_URL
  if (explicit) {
    return stripTrailingSlash(explicit)
  }
  const api = getApiBaseUrl()
  if (api) {
    return api.replace(/^http/i, 'ws')
  }
  const { protocol, host } = window.location
  return `${protocol === 'https:' ? 'wss:' : 'ws:'}//${host}`
}
