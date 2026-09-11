import type { ClientToServerEvent, ServerMessage } from '../types'
import { SERVER_TO_CLIENT_EVENTS } from '../types'

/**
 * Connection lifecycle as the UI sees it:
 * - ``connecting`` / ``open`` / ``reconnecting`` — normal operation;
 * - ``lost`` — gave up after repeated failures (e.g. the server restarted and
 *   the room no longer exists);
 * - ``removed`` — the host removed this player;
 * - ``closed`` — closed on purpose by the app.
 */
export type SocketStatus = 'connecting' | 'open' | 'reconnecting' | 'lost' | 'removed' | 'closed'

export const REMOVED_CLOSE_CODE = 4000
export const MAX_FAILED_ATTEMPTS = 6
const BACKOFF_MS = [500, 1000, 2000, 4000, 8000]
const OPEN = 1

export type SocketFactory = (url: string, protocols: string[]) => WebSocket

export interface GameSocketOptions {
  url: string
  protocols: string[]
  gameId: string
  onMessage: (message: ServerMessage, receivedAt: number) => void
  onStatus: (status: SocketStatus) => void
  createSocket?: SocketFactory
  now?: () => number
}

const KNOWN_EVENTS = new Set<string>(SERVER_TO_CLIENT_EVENTS)

function parseMessage(raw: unknown): ServerMessage | null {
  if (typeof raw !== 'string') {
    return null
  }
  try {
    const data: unknown = JSON.parse(raw)
    if (
      typeof data === 'object' &&
      data !== null &&
      typeof (data as { event?: unknown }).event === 'string' &&
      KNOWN_EVENTS.has((data as { event: string }).event) &&
      typeof (data as { game_id?: unknown }).game_id === 'string' &&
      typeof (data as { timestamp?: unknown }).timestamp === 'string' &&
      (data as { payload?: unknown }).payload !== null &&
      !Array.isArray((data as { payload?: unknown }).payload) &&
      typeof (data as { payload?: unknown }).payload === 'object'
    ) {
      return data as ServerMessage
    }
  } catch {
    // Unknown or malformed messages are ignored (§14.3 forward compatibility).
  }
  return null
}

/**
 * One realtime connection with the standard envelope and automatic
 * reconnection. The server re-sends the full current state on every
 * (re)connect, so reconnecting is always safe.
 */
export class GameSocket {
  private socket: WebSocket | null = null
  private failedAttempts = 0
  private timer: ReturnType<typeof setTimeout> | null = null
  private stopped = false
  private readonly options: GameSocketOptions

  constructor(options: GameSocketOptions) {
    this.options = options
  }

  connect(): void {
    this.stopped = false
    this.failedAttempts = 0
    this.open()
  }

  /** Send one intent; returns false when not currently connected. */
  send(event: ClientToServerEvent, payload: Record<string, unknown> = {}): boolean {
    if (this.socket === null || this.socket.readyState !== OPEN) {
      return false
    }
    try {
      this.socket.send(
      JSON.stringify({
        event,
        payload,
        timestamp: new Date().toISOString(),
        game_id: this.options.gameId,
      }),
      )
      return true
    } catch {
      return false
    }
  }

  close(): void {
    this.stopped = true
    this.clearTimer()
    const socket = this.socket
    this.socket = null
    socket?.close(1000)
    this.options.onStatus('closed')
  }

  private open(): void {
    const create: SocketFactory =
      this.options.createSocket ?? ((url, protocols) => new WebSocket(url, protocols))
    this.options.onStatus(this.failedAttempts === 0 ? 'connecting' : 'reconnecting')

    let socket: WebSocket
    try {
      socket = create(this.options.url, this.options.protocols)
    } catch {
      this.failedAttempts += 1
      this.scheduleReconnect()
      return
    }
    this.socket = socket
    let opened = false

    socket.onopen = () => {
      if (this.stopped || this.socket !== socket) return
      opened = true
      this.failedAttempts = 0
      this.options.onStatus('open')
    }
    socket.onmessage = (event: MessageEvent) => {
      if (this.stopped || this.socket !== socket) return
      const message = parseMessage(event.data)
      if (message !== null && message.game_id === this.options.gameId) {
        this.options.onMessage(message, (this.options.now ?? Date.now)())
      }
    }
    socket.onclose = (event: CloseEvent) => {
      if (this.socket !== socket) return
      if (this.socket === socket) {
        this.socket = null
      }
      if (this.stopped) {
        return
      }
      if (event.code === REMOVED_CLOSE_CODE) {
        this.stopped = true
        this.options.onStatus('removed')
        return
      }
      if (!opened) {
        this.failedAttempts += 1
      }
      this.scheduleReconnect()
    }
  }

  private scheduleReconnect(): void {
    if (this.failedAttempts >= MAX_FAILED_ATTEMPTS) {
      this.stopped = true
      this.options.onStatus('lost')
      return
    }
    this.options.onStatus('reconnecting')
    const delay = BACKOFF_MS[Math.min(this.failedAttempts, BACKOFF_MS.length - 1)]
    this.clearTimer()
    this.timer = setTimeout(() => {
      this.timer = null
      if (!this.stopped) {
        this.open()
      }
    }, delay)
  }

  private clearTimer(): void {
    if (this.timer !== null) {
      clearTimeout(this.timer)
      this.timer = null
    }
  }
}
