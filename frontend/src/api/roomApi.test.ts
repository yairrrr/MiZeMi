import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import type {
  CreateRoomResponse,
  ErrorResponse,
  JoinRoomRequest,
  JoinRoomResponse,
  Player,
} from '../types'
import { createRoom, joinRoom, RestApiError } from './roomApi'

const createRoomResponse: CreateRoomResponse = {
  room_code: 'K7PW3N',
  game_id: 'game-123',
}

const playerResponse: Player = {
  player_id: 'player-123',
  display_name: 'Dana',
  is_host: false,
  connected: false,
  has_profile: false,
  is_ready: false,
  score: 0,
}

const joinRoomResponse: JoinRoomResponse = {
  game_id: 'game-123',
  player: playerResponse,
}

function jsonResponse(body: unknown, status: number): Response {
  return {
    json: async () => body,
    ok: status >= 200 && status < 300,
    status,
  } as Response
}

describe('room REST API', () => {
  const fetchMock = vi.fn<typeof fetch>()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
    vi.stubEnv('VITE_MIZEMI_API_BASE_URL', 'https://api.example.test/')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  test('createRoom posts to the approved endpoint without a request payload', async () => {
    fetchMock.mockResolvedValue(jsonResponse(createRoomResponse, 201))

    await createRoom()

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.test/api/v1/rooms',
      { method: 'POST' },
    )
  })

  test('createRoom returns the approved response', async () => {
    fetchMock.mockResolvedValue(jsonResponse(createRoomResponse, 201))

    await expect(createRoom()).resolves.toEqual(createRoomResponse)
  })

  test('createRoom uses the relative same-origin URL when the API base URL is not defined', async () => {
    vi.stubEnv('VITE_MIZEMI_API_BASE_URL', undefined)
    fetchMock.mockResolvedValue(jsonResponse(createRoomResponse, 201))

    await createRoom()

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/rooms', { method: 'POST' })
  })

  test('joinRoom encodes the room code and sends exactly the join request', async () => {
    const request: JoinRoomRequest = { display_name: 'Dana' }
    fetchMock.mockResolvedValue(jsonResponse(joinRoomResponse, 201))

    await joinRoom('room /?', request)

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.test/api/v1/rooms/room%20%2F%3F/players',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      },
    )
  })

  test('joinRoom returns the approved response with game_id and Player', async () => {
    fetchMock.mockResolvedValue(jsonResponse(joinRoomResponse, 201))

    await expect(
      joinRoom('K7PW3N', { display_name: 'Dana' }),
    ).resolves.toEqual(joinRoomResponse)
  })

  test('preserves the approved error response for non-success responses', async () => {
    const errorResponse: ErrorResponse = {
      error: {
        code: 'NAME_TAKEN',
        message: 'That display name is already taken in this room.',
        details: { room_code: 'K7PW3N' },
      },
    }
    fetchMock.mockResolvedValue(jsonResponse(errorResponse, 409))

    const request = joinRoom('K7PW3N', { display_name: 'Dana' })

    await expect(request).rejects.toMatchObject({
      name: 'RestApiError',
      message: errorResponse.error.message,
      status: 409,
      response: errorResponse,
    } satisfies Partial<RestApiError>)
  })
})
