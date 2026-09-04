import { useRef, useState } from 'react'

import { createRoom, RestApiError } from '../../api/roomApi'
import type { CreateRoomResponse } from '../../types'

const GENERIC_CREATE_ERROR = 'We could not create a room. Please try again.'

export function HostRoomEntry() {
  const [room, setRoom] = useState<CreateRoomResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const isPending = useRef(false)

  async function handleCreateRoom() {
    if (isPending.current) {
      return
    }

    isPending.current = true
    setIsLoading(true)
    setErrorMessage(null)

    try {
      setRoom(await createRoom())
    } catch (error) {
      setErrorMessage(
        error instanceof RestApiError
          ? error.response.error.message
          : GENERIC_CREATE_ERROR,
      )
    } finally {
      isPending.current = false
      setIsLoading(false)
    }
  }

  return (
    <section className="entry-card host-card" aria-labelledby="host-title">
      <div className="card-heading">
        <span className="card-icon" aria-hidden="true">
          ✦
        </span>
        <div>
          <p className="card-kicker">Hosting the group?</p>
          <h2 id="host-title">Start a new room</h2>
        </div>
      </div>
      <p className="card-copy">
        Create a room, then share the code so everyone can join the fun.
      </p>

      <button
        className="primary-button host-button"
        type="button"
        disabled={isLoading}
        onClick={handleCreateRoom}
      >
        {isLoading ? 'Creating room…' : 'Create Room'}
      </button>

      {errorMessage !== null && (
        <p className="status-message error-message" role="alert">
          {errorMessage}
        </p>
      )}

      {room !== null && (
        <div className="room-success" role="status" aria-live="polite">
          <p>Your room is ready!</p>
          <strong aria-label={`Room code ${room.room_code}`}>
            {room.room_code}
          </strong>
          <span>Share this code with your players.</span>
        </div>
      )}
    </section>
  )
}
