import { getApiBaseUrl } from '../config'
import type {
  CreateRoomResponse,
  GameConfig,
  ErrorResponse,
  JoinRoomRequest,
  JoinRoomResponse,
} from '../types'

const API_PREFIX = '/api/v1'
const UNAVAILABLE_MESSAGE =
  'The game server is not responding. It may be waking up — please try again in a moment.'

export class RestApiError extends Error {
  readonly status: number
  readonly response: ErrorResponse

  constructor(status: number, response: ErrorResponse) {
    super(response.error.message)
    this.name = 'RestApiError'
    this.status = status
    this.response = response
  }
}

function buildApiUrl(path: string): string {
  return `${getApiBaseUrl()}${API_PREFIX}${path}`
}

function isErrorResponse(body: unknown): body is ErrorResponse {
  if (typeof body !== 'object' || body === null || !('error' in body)) {
    return false
  }
  const error = (body as { error: unknown }).error
  return (
    typeof error === 'object' &&
    error !== null &&
    typeof (error as { message?: unknown }).message === 'string'
  )
}

async function readResponse<T>(response: Response): Promise<T> {
  let body: unknown
  try {
    body = await response.json()
  } catch {
    body = undefined
  }

  if (!response.ok) {
    // A sleeping or failing host may answer with HTML instead of §17 JSON.
    throw new RestApiError(
      response.status,
      isErrorResponse(body)
        ? body
        : { error: { code: 'INTERNAL_ERROR', message: UNAVAILABLE_MESSAGE } },
    )
  }
  return body as T
}

export async function createRoom(config?: GameConfig): Promise<CreateRoomResponse> {
  const response = await fetch(buildApiUrl('/rooms'), {
    method: 'POST',
    ...(config === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config) }),
  })

  return readResponse<CreateRoomResponse>(response)
}

export async function joinRoom(
  roomCode: string,
  request: JoinRoomRequest,
): Promise<JoinRoomResponse> {
  const response = await fetch(
    buildApiUrl(`/rooms/${encodeURIComponent(roomCode)}/players`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    },
  )

  return readResponse<JoinRoomResponse>(response)
}

export const MAX_SUGGESTIONS = 5

/**
 * Up to five reference names completing a partially typed profile answer.
 * Best effort: any failure (sleeping server, abort, bad body) yields none.
 */
export async function fetchSuggestions(field: string, query: string, signal?: AbortSignal): Promise<string[]> {
  const params = new URLSearchParams({ field, q: query })
  try {
    const response = await fetch(buildApiUrl(`/suggestions?${params}`), { signal, credentials: 'omit' })
    if (!response.ok) return []
    const body: unknown = await response.json()
    const suggestions = (body as { suggestions?: unknown } | null)?.suggestions
    if (!Array.isArray(suggestions)) return []
    return suggestions.filter((item): item is string => typeof item === 'string').slice(0, MAX_SUGGESTIONS)
  } catch {
    return []
  }
}
