import type {
  CreateRoomResponse,
  ErrorResponse,
  JoinRoomRequest,
  Player,
} from '../types'

const API_PREFIX = '/api/v1'

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
  const baseUrl = import.meta.env.VITE_MIZEMI_API_BASE_URL ?? ''
  return `${baseUrl.replace(/\/+$/, '')}${API_PREFIX}${path}`
}

async function readResponse<T>(response: Response): Promise<T> {
  const body: unknown = await response.json()

  if (!response.ok) {
    throw new RestApiError(response.status, body as ErrorResponse)
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
): Promise<Player> {
  const response = await fetch(
    buildApiUrl(`/rooms/${encodeURIComponent(roomCode)}/players`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    },
  )

  return readResponse<Player>(response)
}
