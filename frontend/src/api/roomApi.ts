import { getApiBaseUrl } from '../config'
import type {
  CreateRoomResponse,
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

export async function createRoom(): Promise<CreateRoomResponse> {
  const response = await fetch(buildApiUrl('/rooms'), {
    method: 'POST',
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
