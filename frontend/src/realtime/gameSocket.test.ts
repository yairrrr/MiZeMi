import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import { GameSocket, MAX_FAILED_ATTEMPTS, REMOVED_CLOSE_CODE, type SocketStatus } from './gameSocket'

class FakeSocket {
  static instances: FakeSocket[] = []
  readyState = 0
  sent: string[] = []
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  readonly url: string
  readonly protocols: string[]

  constructor(url: string, protocols: string[]) {
    this.url = url
    this.protocols = protocols
    FakeSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close(code = 1000) {
    this.readyState = 3
    this.onclose?.({ code } as CloseEvent)
  }

  open() {
    this.readyState = 1
    this.onopen?.(new Event('open'))
  }

  receive(data: unknown) {
    this.onmessage?.({ data: typeof data === 'string' ? data : JSON.stringify(data) } as MessageEvent)
  }

  drop(code = 1006) {
    this.readyState = 3
    this.onclose?.({ code } as CloseEvent)
  }
}

function setup() {
  const statuses: SocketStatus[] = []
  const messages: unknown[] = []
  const socket = new GameSocket({
    url: 'ws://example.test/ws/rooms/K7PW3N?player_id=p1',
    protocols: ['mizemi.player', 'token-1'],
    gameId: 'game-1',
    onMessage: (message) => messages.push(message),
    onStatus: (status) => statuses.push(status),
    createSocket: (url, protocols) => new FakeSocket(url, protocols) as unknown as WebSocket,
  })
  return { socket, statuses, messages }
}

const latest = () => FakeSocket.instances[FakeSocket.instances.length - 1]

describe('GameSocket', () => {
  beforeEach(() => {
    FakeSocket.instances = []
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  test('opens with the credential subprotocols', () => {
    const { socket, statuses } = setup()
    socket.connect()
    latest().open()

    expect(latest().protocols).toEqual(['mizemi.player', 'token-1'])
    expect(statuses).toEqual(['connecting', 'open'])
  })

  test('sends the standard envelope with the game id and a UTC timestamp', () => {
    const { socket } = setup()
    socket.connect()
    latest().open()

    expect(socket.send('player.ready')).toBe(true)
    const sent = JSON.parse(latest().sent[0])
    expect(Object.keys(sent).sort()).toEqual(['event', 'game_id', 'payload', 'timestamp'])
    expect(sent).toMatchObject({ event: 'player.ready', payload: {}, game_id: 'game-1' })
    expect(sent.timestamp).toMatch(/Z$/)
  })

  test('refuses to send while not connected', () => {
    const { socket } = setup()
    socket.connect()
    expect(socket.send('player.ready')).toBe(false)
  })

  test('delivers known messages and ignores unknown or malformed ones', () => {
    const { socket, messages } = setup()
    socket.connect()
    latest().open()

    latest().receive({ event: 'room.updated', payload: { room_code: 'K7PW3N' }, timestamp: 'x', game_id: 'game-1' })
    latest().receive({ event: 'mystery.event', payload: {}, timestamp: 'x', game_id: 'game-1' })
    latest().receive('not json')

    expect(messages).toHaveLength(1)
  })

  test('reconnects after a dropped connection', () => {
    const { socket, statuses } = setup()
    socket.connect()
    latest().open()
    latest().drop()

    expect(statuses.at(-1)).toBe('reconnecting')
    vi.advanceTimersByTime(600)
    expect(FakeSocket.instances).toHaveLength(2)
    latest().open()
    expect(statuses.at(-1)).toBe('open')
  })

  test('gives up after repeated failed attempts', () => {
    const { socket, statuses } = setup()
    socket.connect()
    for (let attempt = 0; attempt < MAX_FAILED_ATTEMPTS; attempt += 1) {
      latest().drop()
      vi.advanceTimersByTime(10_000)
    }

    expect(statuses.at(-1)).toBe('lost')
    const count = FakeSocket.instances.length
    vi.advanceTimersByTime(60_000)
    expect(FakeSocket.instances).toHaveLength(count)
  })

  test('stops for good when the host removes the player', () => {
    const { socket, statuses } = setup()
    socket.connect()
    latest().open()
    latest().drop(REMOVED_CLOSE_CODE)

    expect(statuses.at(-1)).toBe('removed')
    vi.advanceTimersByTime(60_000)
    expect(FakeSocket.instances).toHaveLength(1)
  })

  test('close() stops reconnecting', () => {
    const { socket, statuses } = setup()
    socket.connect()
    latest().open()
    socket.close()
    vi.advanceTimersByTime(60_000)

    expect(statuses.at(-1)).toBe('closed')
    expect(FakeSocket.instances).toHaveLength(1)
  })
})

 test('ignores messages from another game and from a closed socket', () => {
  const { socket, messages } = setup()
  socket.connect()
  const old = latest()
  old.open()
  old.receive({ event: 'room.updated', payload: {}, timestamp: 'x', game_id: 'other-game' })
  old.receive({ event: 'room.updated', payload: null, timestamp: 'x', game_id: 'game-1' })
  socket.close()
  old.receive({ event: 'room.updated', payload: {}, timestamp: 'x', game_id: 'game-1' })
  expect(messages).toEqual([])
 })
