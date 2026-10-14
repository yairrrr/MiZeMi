import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import { RestApiError } from '../api/roomApi'
import type {
  CreateRoomResponse,
  ErrorResponse,
  JoinRoomResponse,
  Player,
} from '../types'
import { App } from './App'

vi.mock('../hooks/useGameConnection', async () => {
  const { initialGameView } = await import('../state/gameReducer')
  return {
    useGameConnection: () => ({
      view: initialGameView,
      status: 'connecting',
      send: () => true,
      dismissError: () => {},
    }),
  }
})

vi.mock('../api/roomApi', async (importOriginal) => {
  const original = await importOriginal<typeof import('../api/roomApi')>()
  return { ...original, createRoom: vi.fn(), joinRoom: vi.fn() }
})

import { createRoom, joinRoom } from '../api/roomApi'

const createRoomMock = vi.mocked(createRoom)
const joinRoomMock = vi.mocked(joinRoom)
const createdRoom: CreateRoomResponse = { config: { question_count: 20, language: 'en', question_source: 'algorithmic' }, room_code: 'K7PW3N', game_id: 'game-123', host_token: 'host-secret' }
const joinedPlayer: Player = {
  player_id: 'player-123', display_name: 'Dana', is_host: false, connected: false,
  has_profile: false, is_ready: false, score: 0,
}
const joinResponse: JoinRoomResponse = {
  game_id: 'game-123',
  player: joinedPlayer,
  player_token: 'player-secret',
}

afterEach(cleanup)

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((promiseResolve) => { resolve = promiseResolve })
  return { promise, resolve }
}

async function fillJoinForm(roomCode = 'K7PW3N', displayName = 'Dana') {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Room Code'), roomCode)
  await user.type(screen.getByLabelText('Display Name'), displayName)
  return user
}

describe('room entry screen', () => {
  beforeEach(() => {
    createRoomMock.mockReset()
    joinRoomMock.mockReset()
    sessionStorage.clear()
  })

  test('renders the MiZeMi shell with Host and Player actions', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: 'MiZeMi' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Create Room' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Join Room' })).toBeVisible()
  })

  test('creates once and disables duplicate submissions while pending', async () => {
    const result = deferred<CreateRoomResponse>()
    createRoomMock.mockReturnValue(result.promise)
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Create Room' }))
    expect(createRoomMock).toHaveBeenCalledOnce()
    const loadingButton = screen.getByRole('button', { name: 'Creating room…' })
    expect(loadingButton).toBeDisabled()
    await user.click(loadingButton)
    expect(createRoomMock).toHaveBeenCalledOnce()
    result.resolve(createdRoom)
    expect(await screen.findByText('K7PW3N')).toBeVisible()
  })

  test('shows the server-owned Create Room error message', async () => {
    const response: ErrorResponse = { error: { code: 'INTERNAL_ERROR', message: 'Rooms are taking a short break.' } }
    createRoomMock.mockRejectedValue(new RestApiError(500, response))
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Create Room' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(response.error.message)
  })

  test('joins with the entered room code and exact display_name shape', async () => {
    joinRoomMock.mockResolvedValue(joinResponse)
    render(<App />)
    const user = await fillJoinForm('room-7', 'Dana')
    await user.click(screen.getByRole('button', { name: 'Join Room' }))
    expect(joinRoomMock).toHaveBeenCalledWith('room-7', { display_name: 'Dana' })
  })

  test('keeps the session so a refresh returns to the same room', async () => {
    joinRoomMock.mockResolvedValue(joinResponse)
    render(<App />)
    const user = await fillJoinForm()
    await user.click(screen.getByRole('button', { name: 'Join Room' }))
    await screen.findByText(/you’re in, Dana!/i)

    const stored = JSON.parse(sessionStorage.getItem('mizemi.session') ?? '{}')
    expect(stored).toMatchObject({ role: 'player', room_code: 'K7PW3N', player_id: 'player-123' })

    cleanup()
    render(<App />)
    expect(await screen.findByText(/you’re in, Dana!/i)).toBeVisible()
  })

  test('prefills the room code from a shared join link', () => {
    window.history.pushState({}, '', '/?room=AB12CD')
    render(<App />)
    expect(screen.getByLabelText('Room Code')).toHaveValue('AB12CD')
    window.history.pushState({}, '', '/')
  })

  test('disables Join and prevents duplicate submissions while pending', async () => {
    const result = deferred<JoinRoomResponse>()
    joinRoomMock.mockReturnValue(result.promise)
    render(<App />)
    const user = await fillJoinForm()
    await user.click(screen.getByRole('button', { name: 'Join Room' }))
    const loadingButton = screen.getByRole('button', { name: 'Joining…' })
    expect(loadingButton).toBeDisabled()
    await user.click(loadingButton)
    expect(joinRoomMock).toHaveBeenCalledOnce()
    result.resolve(joinResponse)
    expect(await screen.findByText(/you’re in, Dana!/i)).toBeVisible()
  })

  test('renders the authoritative joined Player display name', async () => {
    joinRoomMock.mockResolvedValue({
      ...joinResponse,
      player: { ...joinedPlayer, display_name: 'Dana from server' },
    })
    render(<App />)
    const user = await fillJoinForm()
    await user.click(screen.getByRole('button', { name: 'Join Room' }))
    expect(await screen.findByText(/you’re in, Dana from server!/i)).toBeVisible()
  })

  test('shows a known join REST error message', async () => {
    const response: ErrorResponse = { error: { code: 'ROOM_NOT_FOUND', message: 'No room exists with that code.' } }
    joinRoomMock.mockRejectedValue(new RestApiError(404, response))
    render(<App />)
    const user = await fillJoinForm()
    await user.click(screen.getByRole('button', { name: 'Join Room' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(response.error.message)
  })

  test('shows a safe generic message for unexpected join failures', async () => {
    joinRoomMock.mockRejectedValue(new Error('private network details'))
    render(<App />)
    const user = await fillJoinForm()
    await user.click(screen.getByRole('button', { name: 'Join Room' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('We could not join the room. Please try again.')
    expect(screen.queryByText(/private network details/i)).not.toBeInTheDocument()
  })

  test('requires a non-empty room code before joining', async () => {
    render(<App />)
    const user = await fillJoinForm('   ', 'Dana')
    await user.click(screen.getByRole('button', { name: 'Join Room' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a room code')
    expect(joinRoomMock).not.toHaveBeenCalled()
  })

  test.each([
    ['an empty display name', '   ', 'Enter a display name'],
    ['an overlong display name', '123456789012345678901', '20 characters or fewer'],
  ])('validates %s using approved rules', async (_case, displayName, message) => {
    render(<App />)
    const user = await fillJoinForm('K7PW3N', displayName)
    await user.click(screen.getByRole('button', { name: 'Join Room' }))
    expect(screen.getByRole('alert')).toHaveTextContent(message)
    expect(joinRoomMock).not.toHaveBeenCalled()
  })
})
