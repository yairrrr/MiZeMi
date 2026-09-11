import { type FormEvent, useRef, useState } from 'react'

import { joinRoom, RestApiError } from '../../api/roomApi'
import type { JoinRoomResponse } from '../../types'

const GENERIC_JOIN_ERROR = 'We could not join the room. Please try again.'

export function PlayerRoomEntry({
  initialRoomCode = '',
  onJoined,
}: {
  initialRoomCode?: string
  onJoined: (roomCode: string, response: JoinRoomResponse) => void
}) {
  const [roomCode, setRoomCode] = useState(initialRoomCode)
  const [displayName, setDisplayName] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const isPending = useRef(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (isPending.current) {
      return
    }

    const trimmedDisplayName = displayName.trim()
    if (roomCode.trim().length === 0) {
      setErrorMessage('Enter a room code to continue.')
      return
    }
    if (trimmedDisplayName.length === 0) {
      setErrorMessage('Enter a display name to continue.')
      return
    }
    if (trimmedDisplayName.length > 20) {
      setErrorMessage('Display name must be 20 characters or fewer.')
      return
    }

    isPending.current = true
    setIsLoading(true)
    setErrorMessage(null)

    try {
      const response = await joinRoom(roomCode, { display_name: displayName })
      onJoined(roomCode.trim().toUpperCase(), response)
    } catch (error) {
      setErrorMessage(
        error instanceof RestApiError ? error.response.error.message : GENERIC_JOIN_ERROR,
      )
    } finally {
      isPending.current = false
      setIsLoading(false)
    }
  }

  return (
    <section className="entry-card player-card" aria-labelledby="player-title">
      <div className="card-heading">
        <span className="card-icon" aria-hidden="true">
          →
        </span>
        <div>
          <p className="card-kicker">Ready to play?</p>
          <h2 id="player-title">Join your friends</h2>
        </div>
      </div>
      <p className="card-copy">
        Enter the room code from your host and choose the name everyone will see.
      </p>

      <form className="join-form" onSubmit={handleSubmit} noValidate>
        <label htmlFor="room-code">Room Code</label>
        <input
          id="room-code"
          name="room_code"
          value={roomCode}
          onChange={(event) => setRoomCode(event.target.value)}
          placeholder="e.g. K7PW3N"
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          maxLength={12}
          disabled={isLoading}
        />

        <label htmlFor="display-name">Display Name</label>
        <input
          id="display-name"
          name="display_name"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          placeholder="What should we call you?"
          autoComplete="nickname"
          maxLength={40}
          disabled={isLoading}
        />

        <button className="primary-button join-button" type="submit" disabled={isLoading}>
          {isLoading ? 'Joining…' : 'Join Room'}
        </button>
      </form>

      {errorMessage !== null && (
        <p className="status-message error-message" role="alert">
          {errorMessage}
        </p>
      )}
    </section>
  )
}
