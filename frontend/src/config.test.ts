import { afterEach, describe, expect, test, vi } from 'vitest'

import { getApiBaseUrl, getWebSocketBaseUrl } from './config'
import { buildHostWebSocketUrl } from './realtime/hostWebSocketUrl'

describe('backend URL configuration', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  test('uses same-origin REST by default', () => {
    vi.stubEnv('VITE_MIZEMI_API_BASE_URL', undefined)
    expect(getApiBaseUrl()).toBe('')
  })

  test('strips trailing slashes from the configured API base', () => {
    vi.stubEnv('VITE_MIZEMI_API_BASE_URL', 'https://api.example.test/')
    expect(getApiBaseUrl()).toBe('https://api.example.test')
  })

  test('an explicit WebSocket base wins', () => {
    vi.stubEnv('VITE_MIZEMI_WS_BASE_URL', 'wss://realtime.example.test/')
    expect(getWebSocketBaseUrl()).toBe('wss://realtime.example.test')
  })

  test('derives wss from an https API base', () => {
    vi.stubEnv('VITE_MIZEMI_WS_BASE_URL', undefined)
    vi.stubEnv('VITE_MIZEMI_API_BASE_URL', 'https://api.example.test')
    expect(getWebSocketBaseUrl()).toBe('wss://api.example.test')
  })

  test('supports the Render public URL variables with precedence over legacy names', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://render-api.example.test/')
    vi.stubEnv('VITE_MIZEMI_API_BASE_URL', 'https://legacy.example.test')
    vi.stubEnv('VITE_WS_BASE_URL', 'wss://render-ws.example.test/')
    vi.stubEnv('VITE_MIZEMI_WS_BASE_URL', 'wss://legacy.example.test')
    expect(getApiBaseUrl()).toBe('https://render-api.example.test')
    expect(getWebSocketBaseUrl()).toBe('wss://render-ws.example.test')
  })

  test('falls back to the page origin', () => {
    vi.stubEnv('VITE_MIZEMI_WS_BASE_URL', undefined)
    vi.stubEnv('VITE_MIZEMI_API_BASE_URL', undefined)
    expect(getWebSocketBaseUrl()).toBe(`ws://${window.location.host}`)
  })
})

describe('buildHostWebSocketUrl', () => {
  test('builds the host endpoint without credentials in the URL', () => {
    expect(buildHostWebSocketUrl('wss://api.example.test/base/', 'K7PW3N')).toBe(
      'wss://api.example.test/ws/rooms/K7PW3N/host',
    )
  })
})
