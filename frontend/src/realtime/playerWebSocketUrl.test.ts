import { describe, expect, test } from 'vitest'

import { buildPlayerWebSocketUrl } from './playerWebSocketUrl'

describe('buildPlayerWebSocketUrl', () => {
  test('builds the approved Player WebSocket endpoint', () => {
    expect(
      buildPlayerWebSocketUrl('ws://localhost:8000', 'K7PW3N', 'player-123'),
    ).toBe('ws://localhost:8000/ws/rooms/K7PW3N?player_id=player-123')
  })

  test('uses the approved endpoint from a base URL without a trailing slash', () => {
    expect(
      buildPlayerWebSocketUrl('wss://example.com/realtime', 'ROOM1', 'player-1'),
    ).toBe('wss://example.com/ws/rooms/ROOM1?player_id=player-1')
  })

  test('uses the approved endpoint from a base URL with a trailing slash', () => {
    expect(
      buildPlayerWebSocketUrl('wss://example.com/realtime/', 'ROOM1', 'player-1'),
    ).toBe('wss://example.com/ws/rooms/ROOM1?player_id=player-1')
  })

  test('encodes room_code and player_id as dynamic URL values', () => {
    expect(
      buildPlayerWebSocketUrl(
        'wss://example.com',
        'room /?',
        'player&id=1 ?',
      ),
    ).toBe(
      'wss://example.com/ws/rooms/room%20%2F%3F?player_id=player%26id%3D1+%3F',
    )
  })
})
