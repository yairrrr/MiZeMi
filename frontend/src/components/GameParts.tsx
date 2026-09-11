import { useI18n, publicError } from '../i18n/I18n'
import { useEffect, useState } from 'react'

import type { MessageKey } from '../i18n/messages'
import type { SocketStatus } from '../realtime/gameSocket'
import { remainingMs } from '../state/gameReducer'
import type {
  ErrorResponse,
  LeaderboardEntry,
  Player,
  Question,
  QuestionOption,
  Statistics,
} from '../types'

const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F']

export function optionLetter(index: number): string {
  return LETTERS[index] ?? String(index + 1)
}

/** Countdown driven by the server's question clock, corrected for skew. */
export function Timer({ question, serverOffsetMs }: { question: Question; serverOffsetMs: number }) {
  const { t } = useI18n()
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250)
    return () => clearInterval(id)
  }, [])

  const left = remainingMs(question, serverOffsetMs, now)
  const seconds = Math.ceil(left / 1000)
  const fraction = Math.min(1, left / (question.time_limit_seconds * 1000))

  return (
    <div className={`timer ${seconds <= 5 ? 'timer-urgent' : ''}`} role="timer" aria-label={t('{seconds} seconds left', { seconds })}>
      <div className="timer-track">
        <div className="timer-fill" style={{ width: `${fraction * 100}%` }} />
      </div>
      <span className="timer-seconds">{seconds}</span>
    </div>
  )
}

export function AnswerBars({
  options,
  statistics,
  ownOptionId,
}: {
  options: QuestionOption[]
  statistics: Statistics
  ownOptionId?: string | null
}) {
  const { t } = useI18n()
  const byOption = new Map(statistics.answer_distribution.map((entry) => [entry.option_id, entry]))

  return (
    <ol className="answer-bars" aria-label={t("Answer distribution")}>
      {options.map((option, index) => {
        const entry = byOption.get(option.option_id)
        const percentage = entry?.percentage ?? 0
        const isCorrect = option.option_id === statistics.correct_option_id
        return (
          <li
            key={option.option_id}
            className={`answer-bar option-${index} ${isCorrect ? 'is-correct' : ''} ${
              option.option_id === ownOptionId ? 'is-own' : ''
            }`}
          >
            <div className="answer-bar-label">
              <span className="option-letter">{optionLetter(index)}</span>
              <span className="answer-bar-text"><bdi>{option.text}</bdi></span>
              {option.option_id === ownOptionId && <span className="own-answer-label">{t('Your answer')}</span>}
              {isCorrect && <span className="correct-mark" aria-label={t("Correct answer")}>✓</span>}
            </div>
            <div className="answer-bar-track">
              <div className="answer-bar-fill" style={{ width: `${percentage}%` }} />
            </div>
            <span className="answer-bar-value" dir="ltr">
              {entry?.count ?? 0} · {Math.round(percentage)}%
            </span>
          </li>
        )
      })}
    </ol>
  )
}

const MEDALS = ['🥇', '🥈', '🥉']

export function LeaderboardList({
  entries,
  highlightPlayerId,
  limit,
}: {
  entries: LeaderboardEntry[]
  highlightPlayerId?: string
  limit?: number
}) {
  const { t } = useI18n()
  const shown = limit === undefined ? entries : entries.slice(0, limit)
  return (
    <ol className="leaderboard" aria-label={t("Leaderboard")}>
      {shown.map((entry) => (
        <li
          key={entry.player_id}
          className={`leaderboard-row ${entry.player_id === highlightPlayerId ? 'is-me' : ''}`}
        >
          <span className="leaderboard-rank">{MEDALS[entry.rank - 1] ?? `#${entry.rank}`}</span>
          <span className="leaderboard-name"><bdi>{entry.display_name}</bdi></span>
          <span className="leaderboard-score">{entry.total_score.toLocaleString('en-US')}</span>
        </li>
      ))}
    </ol>
  )
}

export function Winners({ winners }: { winners: LeaderboardEntry[] }) {
  const { t } = useI18n()
  if (winners.length === 0) {
    return <p className="winner-banner">{t("No winner this time.")}</p>
  }
  const names = winners.map((winner) => winner.display_name).join(' & ')
  return (
    <div className="winner-banner" role="status">
      <span className="winner-trophy" aria-hidden="true">🏆</span>
      <p>{t(winners.length > 1 ? "It's a tie!" : 'And the winner is…')}</p>
      <strong><bdi>{names}</bdi></strong>
      <span>{t('{score} points', { score: winners[0].total_score.toLocaleString('en-US') })}</span>
    </div>
  )
}

export function PlayerRoster({
  players,
  onRemove,
}: {
  players: Player[]
  onRemove?: (player: Player) => void
}) {
  const { t } = useI18n()
  if (players.length === 0) {
    return <p className="empty-roster">{t("No players yet — share the room code!")}</p>
  }
  return (
    <ul className="roster" aria-label={t("Players")}>
      {players.map((player) => (
        <li key={player.player_id} className="roster-row">
          <span className={`presence ${player.connected ? 'online' : 'offline'}`} aria-label={t(player.connected ? 'Connected' : 'Disconnected')} />
          <span className="roster-name"><bdi>{player.display_name}</bdi></span>
          <span className={`chip ${player.has_profile ? 'chip-done' : ''}`}>
            {t(player.has_profile ? 'Profile ✓' : 'Profile…')}
          </span>
          <span className={`chip ${player.is_ready ? 'chip-ready' : ''}`}>
            {t(player.is_ready ? 'Ready ✓' : 'Not ready')}
          </span>
          {onRemove && (
            <button
              type="button"
              className="icon-button"
              aria-label={t('Remove {name}', { name: player.display_name })}
              onClick={() => onRemove(player)}
            >
              ×
            </button>
          )}
        </li>
      ))}
    </ul>
  )
}

const STATUS_COPY: Partial<Record<SocketStatus, MessageKey>> = {
  connecting: 'Connecting…',
  reconnecting: 'Connection interrupted — reconnecting…',
  lost: 'We lost the connection to this room. It may have ended or the server restarted.',
}

export function ConnectionBanner({ status, onLeave }: { status: SocketStatus; onLeave: () => void }) {
  const { t } = useI18n()
  const copy = STATUS_COPY[status]
  if (copy === undefined || status === 'connecting') {
    return null
  }
  return (
    <div className={`connection-banner status-${status}`} role="status">
      <span>{t(copy)}</span>
      {status === 'lost' && (
        <button type="button" className="ghost-button" onClick={onLeave}>{t("Back to start")}</button>
      )}
    </div>
  )
}

export function ErrorToast({
  error,
  onDismiss,
}: {
  error: ErrorResponse['error']
  onDismiss: () => void
}) {
  const { t, language } = useI18n()
  return (
    <div className="error-toast" role="alert">
      <span>{publicError(language, error)}</span>
      <button type="button" className="icon-button" aria-label={t("Dismiss")} onClick={onDismiss}>
        ×
      </button>
    </div>
  )
}
