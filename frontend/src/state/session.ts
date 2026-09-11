// The browser-tab session: which room this tab belongs to and its credential.
// sessionStorage is per tab, so several players can test from one browser,
// and a page refresh reconnects to the same room instead of losing the seat.

export type HostSession = {
  role: 'host'
  room_code: string
  game_id: string
  host_token: string
}

export type PlayerSession = {
  role: 'player'
  room_code: string
  game_id: string
  player_id: string
  player_token: string
  display_name: string
}

export type Session = HostSession | PlayerSession

const STORAGE_KEY = 'mizemi.session'

function storage(): Storage | null {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

function isString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0
}

function isSession(value: unknown): value is Session {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const candidate = value as Record<string, unknown>
  if (!isString(candidate.room_code) || !isString(candidate.game_id)) {
    return false
  }
  if (candidate.role === 'host') {
    return isString(candidate.host_token)
  }
  if (candidate.role === 'player') {
    return (
      isString(candidate.player_id) &&
      isString(candidate.player_token) &&
      isString(candidate.display_name)
    )
  }
  return false
}

export function loadSession(): Session | null {
  try {
    const raw = storage()?.getItem(STORAGE_KEY)
    if (!raw) {
      return null
    }
    const parsed: unknown = JSON.parse(raw)
    return isSession(parsed) ? parsed : null
  } catch {
    return null
  }
}

export function saveSession(session: Session): void {
  try {
    storage()?.setItem(STORAGE_KEY, JSON.stringify(session))
  } catch {
    // Private browsing may block storage; the game still works for this page.
  }
}

export function clearSession(): void {
  try {
    storage()?.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}
