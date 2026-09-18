import { useI18n, publicError, direction } from '../../i18n/I18n'
import { type FormEvent, useRef, useState } from 'react'

import { joinRoom, RestApiError } from '../../api/roomApi'
import type { MessageKey } from '../../i18n/messages'
import type { ErrorResponse, JoinRoomResponse } from '../../types'

const GENERIC_JOIN_ERROR = 'We could not join the room. Please try again.'

export function PlayerRoomEntry({
  initialRoomCode = '',
  onJoined,
}: {
  initialRoomCode?: string
  onJoined: (roomCode: string, response: JoinRoomResponse) => void
}) {
  const { t, language } = useI18n()
  const [roomCode, setRoomCode] = useState(initialRoomCode)
  const [displayName, setDisplayName] = useState('')
  const [errorMessage, setErrorMessage] = useState<MessageKey | ErrorResponse['error'] | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const isPending = useRef(false)
  const [invalidField, setInvalidField] = useState<'room-code' | 'display-name' | null>(null)

  function invalid(field: 'room-code' | 'display-name', message: MessageKey) {
    setInvalidField(field)
    setErrorMessage(message)
    document.getElementById(field)?.focus()
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (isPending.current) {
      return
    }

    const trimmedDisplayName = displayName.trim()
    if (roomCode.trim().length === 0) {
      invalid('room-code', 'Enter a room code to continue.')
      return
    }
    if (trimmedDisplayName.length === 0) {
      invalid('display-name', 'Enter a display name to continue.')
      return
    }
    if (trimmedDisplayName.length > 20) {
      invalid('display-name', 'Display name must be 20 characters or fewer.')
      return
    }

    isPending.current = true
    setIsLoading(true)
    setErrorMessage(null)
    setInvalidField(null)

    try {
      const response = await joinRoom(roomCode, { display_name: displayName })
      onJoined(roomCode.trim().toUpperCase(), response)
    } catch (error) {
      setErrorMessage(
        error instanceof RestApiError ? error.response.error : GENERIC_JOIN_ERROR,
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
          <p className="card-kicker">{t("Ready to play?")}</p>
          <h2 id="player-title">{t("Join your friends")}</h2>
        </div>
      </div>
      <p className="card-copy">{t("Enter the room code from your host and choose the name everyone will see.")}</p>

      <form className="join-form" onSubmit={handleSubmit} noValidate>
        <label htmlFor="room-code">{t("Room Code")}</label>
        <input
          id="room-code"
          required aria-required="true"
          aria-invalid={invalidField === 'room-code' || undefined}
          aria-describedby={invalidField === 'room-code' ? 'join-entry-error' : undefined}
          dir="ltr"
          name="room_code"
          value={roomCode}
          onChange={(event) => setRoomCode(event.target.value)}
          placeholder={t("e.g. K7PW3N")}
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          maxLength={12}
          disabled={isLoading}
        />

        <label htmlFor="display-name">{t("Display Name")}</label>
        <input
          id="display-name"
          required aria-required="true"
          aria-invalid={invalidField === 'display-name' || undefined}
          aria-describedby={invalidField === 'display-name' ? 'join-entry-error' : undefined}
          dir={displayName ? 'auto' : direction(language)}
          name="display_name"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          placeholder={t("What should we call you?")}
          autoComplete="nickname"
          maxLength={40}
          disabled={isLoading}
        />

        <button className="primary-button join-button" type="submit" disabled={isLoading}>
          {t(isLoading ? 'Joining…' : 'Join Room')}
        </button>
      </form>

      {errorMessage !== null && (
        <p id="join-entry-error" className="status-message error-message" role="alert">
          {typeof errorMessage === 'string' ? t(errorMessage) : publicError(language, errorMessage)}
        </p>
      )}
    </section>
  )
}
