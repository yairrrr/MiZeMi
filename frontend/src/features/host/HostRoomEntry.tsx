import { useRef, useState, type FormEvent } from 'react'
import { createRoom, RestApiError } from '../../api/roomApi'
import { publicError, useI18n } from '../../i18n/I18n'
import type { Language, MessageKey } from '../../i18n/messages'
import type { CreateRoomResponse, ErrorResponse } from '../../types'

export function HostRoomEntry({ onCreated }: { onCreated: (room: CreateRoomResponse) => void }) {
  const { t, language } = useI18n()
  const [error, setError] = useState<MessageKey | ErrorResponse['error'] | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [count, setCount] = useState('20')
  const [gameLanguage, setGameLanguage] = useState<Language | null>(null)
  const isPending = useRef(false)

  async function handleCreateRoom(event: FormEvent) {
    event.preventDefault()
    if (isPending.current) return
    const questionCount = Number(count)
    if (!/^\d+$/.test(count) || !Number.isInteger(questionCount) || questionCount < 1 || questionCount > 50) {
      setError('Choose a whole number from 1 to 50.')
      return
    }
    isPending.current = true
    setIsLoading(true)
    setError(null)
    try {
      onCreated(await createRoom({ question_count: questionCount, language: gameLanguage ?? language }))
    } catch (error) {
      setError(error instanceof RestApiError ? error.response.error : 'We could not create a room. Please try again.')
    } finally {
      isPending.current = false
      setIsLoading(false)
    }
  }

  return (
    <section className="entry-card host-card" aria-labelledby="host-title">
      <div className="card-heading">
        <span className="card-icon" aria-hidden="true">✦</span>
        <div><p className="card-kicker">{t('Hosting the group?')}</p><h2 id="host-title">{t('Start a new room')}</h2></div>
      </div>
      <p className="card-copy">{t('Create a room on the big screen, then share the code so everyone can join from their phone.')}</p>
      <form onSubmit={handleCreateRoom} noValidate>
        <fieldset className="room-settings" disabled={isLoading}>
          <label htmlFor="question-count">{t('Number of questions')}</label>
          <div className="count-stepper" dir="ltr">
            <button type="button" aria-label={t('Fewer questions')} disabled={Number(count) <= 1}
              onClick={() => setCount(String(Math.max(1, (Number(count) || 20) - 1)))}>−</button>
            <input id="question-count" type="number" inputMode="numeric" min={1} max={50} step={1}
              value={count} onChange={(e) => setCount(e.target.value)} aria-describedby="count-help" />
            <button type="button" aria-label={t('More questions')} disabled={Number(count) >= 50}
              onClick={() => setCount(String(Math.min(50, (Number(count) || 20) + 1)))}>+</button>
          </div>
          <small id="count-help">{t('Choose 1–50 questions.')}</small>
          <label htmlFor="game-language">{t('Game language')}</label>
          <select id="game-language" value={gameLanguage ?? language}
            onChange={(e) => setGameLanguage(e.target.value === 'he' ? 'he' : 'en')}>
            <option value="en">{t('English')}</option><option value="he">{t('Hebrew')}</option>
          </select>
          <small>{t('Everyone receives the same questions in this language.')}</small>
          <button className="primary-button host-button" type="submit">
            {t(isLoading ? 'Creating room…' : 'Create Room')}
          </button>
        </fieldset>
      </form>
      {error !== null && <p className="status-message error-message" role="alert">
        {typeof error === 'string' ? t(error) : publicError(language, error)}
      </p>}
    </section>
  )
}
