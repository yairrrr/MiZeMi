import { useI18n, direction } from '../../i18n/I18n'
import { useEffect, useState } from 'react'

import {
  AnswerBars,
  ConnectionBanner,
  ErrorToast,
  LeaderboardList,
  optionLetter,
  Timer,
  Winners,
} from '../../components/GameParts'
import { type SendFn, useGameConnection } from '../../hooks/useGameConnection'
import type { SocketStatus } from '../../realtime/gameSocket'
import type { GameView } from '../../state/gameReducer'
import type { PlayerSession } from '../../state/session'
import type { Player, Question, RoomSnapshot } from '../../types'
import { ProfileForm } from './ProfileForm'

type PlayerGameViewProps = {
  session: PlayerSession
  view: GameView
  status: SocketStatus
  send: SendFn
  dismissError: () => void
  onLeave: () => void
}

export function PlayerGame({ session, onLeave }: { session: PlayerSession; onLeave: () => void }) {
  const connection = useGameConnection(session)
  return <PlayerGameView session={session} onLeave={onLeave} {...connection} />
}

export function PlayerGameView({ session, view, status, send, dismissError, onLeave }: PlayerGameViewProps) {
  const { t } = useI18n()
  const room = view.room
  const me = room?.players.find((player) => player.player_id === session.player_id) ?? null

  if (status === 'removed' || (room !== null && me === null)) {
    return (
      <section className="game-shell player-shell">
        <div className="stage centered-stage">
          <h2>{t("You left the room")}</h2>
          <p className="card-copy">{t("The host removed you from this game.")}</p>
          <button type="button" className="primary-button" onClick={onLeave}>{t("Back to start")}</button>
        </div>
      </section>
    )
  }

  return (
    <section className="game-shell player-shell" aria-label={t("Player screen")}>
      <header className="game-header compact">
        <div>
          <p className="eyebrow">{t('Room {code}', { code: session.room_code })}</p>
          <strong className="player-name"><bdi>{session.display_name}</bdi></strong>
        </div>
        {me !== null && room !== null && !['LOBBY', 'PROFILE_COLLECTION', 'READY'].includes(room.state) && (
          <span className="score-pill" aria-label={t("Your score")}>
            {t('{score} pts', { score: me.score.toLocaleString('en-US') })}
          </span>
        )}
      </header>

      <ConnectionBanner status={status} onLeave={onLeave} />
      {view.error !== null && <ErrorToast error={view.error} onDismiss={dismissError} />}

      {room === null || me === null ? (
        <div className="stage centered-stage">
          <p className="eyebrow">{t('You’re in, {name}!', { name: session.display_name })}</p>
          <p className="waiting-copy">{t("Connecting to the room…")}</p>
        </div>
      ) : (
        <fieldset className="stage-controls" disabled={status !== 'open'}>
          <PlayerStage session={session} room={room} me={me} view={view} send={send} onLeave={onLeave} connected={status === 'open'} />
        </fieldset>
      )}
    </section>
  )
}

function PlayerStage({
  session,
  room,
  me,
  view,
  send,
  onLeave,
  connected,
}: {
  session: PlayerSession
  room: RoomSnapshot
  me: Player
  view: GameView
  send: SendFn
  onLeave: () => void
  connected: boolean
}) {
  const { t } = useI18n()
  switch (room.state) {
    case 'LOBBY':
    case 'PROFILE_COLLECTION':
    case 'READY':
      if (!me.has_profile) {
        return (
          <ProfileForm
            playerId={session.player_id}
            displayName={session.display_name}
            send={send}
            serverError={view.error}
            connected={connected}
          />
        )
      }
      return <PlayerLobby room={room} me={me} send={send} />
    case 'QUESTION_ACTIVE':
      return view.question === null ? (
        <p className="waiting-copy">{t("Get ready…")}</p>
      ) : (
        <PlayerQuestion key={view.question.question_id} question={view.question} view={view} send={send} connected={connected} />
      )
    case 'QUESTION_RESULTS':
      return <PlayerResults view={view} />
    case 'LEADERBOARD':
      return (
        <div className="stage leaderboard-stage">
          <h2>{t("Leaderboard")}</h2>
          <LeaderboardList entries={view.leaderboard ?? []} highlightPlayerId={me.player_id} />
          <p className="waiting-copy">{t("Waiting for the host…")}</p>
        </div>
      )
    case 'FINISHED':
      return <PlayerFinal view={view} me={me} onLeave={onLeave} />
  }
}

function PlayerLobby({ room, me, send }: { room: RoomSnapshot; me: Player; send: SendFn }) {
  const { t } = useI18n()
  const readyCount = room.players.filter((player) => player.is_ready).length
  if (!me.is_ready) {
    return (
      <div className="stage centered-stage">
        <span className="big-check" aria-hidden="true">✓</span>
        <h2>{t("Profile saved!")}</h2>
        <p className="card-copy">{t("Tap ready when you’re set. The game starts once everyone is ready.")}</p>
        <button type="button" className="primary-button join-button" onClick={() => send('player.ready')}>{t("I’m ready")}</button>
      </div>
    )
  }
  return (
    <div className="stage centered-stage">
      <span className="big-check" aria-hidden="true">🎉</span>
      <h2>{t("You’re ready!")}</h2>
      <p className="card-copy" aria-live="polite">
        {room.state === 'READY'
          ? t('Everyone is ready — waiting for the host to start.')
          : t('{count} of {total} players ready…', { count: readyCount, total: room.players.length })}
      </p>
    </div>
  )
}

function PlayerQuestion({ question, view, send, connected }: { question: Question; view: GameView; send: SendFn; connected: boolean }) {
  const { t } = useI18n()
  const [pending, setPending] = useState<string | null>(null)
  const locked = view.answeredOptionId !== null
  const chosen = view.answeredOptionId ?? pending

  useEffect(() => {
    // A rejected answer (e.g. time is up) releases the pending choice.
    if ((view.error !== null || !connected) && !locked) {
      setPending(null)
    }
  }, [view.error, locked, connected])

  function choose(optionId: string) {
    if (chosen !== null) {
      return
    }
    if (send('answer.submit', { question_id: question.question_id, option_id: optionId })) {
      setPending(optionId)
    }
  }

  const progress = view.progress?.question_id === question.question_id ? view.progress : null

  return (
    <div className="stage question-stage player-question">
      <p className="question-count">
        {t('Question {current} of {total}', { current: question.index + 1, total: question.total_questions })}
      </p>
      <h2 className="question-text" lang={question.language} dir={direction(question.language)}>{question.text}</h2>
      <span className="difficulty-badge">{t(question.difficulty === 'HARD' ? 'Hard' : question.difficulty === 'MEDIUM' ? 'Medium' : 'Easy')}</span>
      <Timer question={question} serverOffsetMs={view.serverOffsetMs} />
      <div className="option-grid player-options" dir={direction(question.language)} role="group" aria-label={t("Answers")}>
        {question.options.map((option, index) => (
          <button
            key={option.option_id}
            type="button"
            className={`option-button option-${index} ${chosen === option.option_id ? 'is-chosen' : ''}`}
            disabled={chosen !== null}
            aria-pressed={chosen === option.option_id}
            onClick={() => choose(option.option_id)}
          >
            <span className="option-letter">{optionLetter(index)}</span>
            <bdi>{option.text}</bdi>
          </button>
        ))}
      </div>
      {chosen !== null && (
        <p className="answer-status" role="status">
          {t(locked ? 'Answer locked in!' : 'Sending…')}
          {progress !== null && ` ${t('{count} of {total} answered.', { count: progress.answered_count, total: progress.player_count })}`}
        </p>
      )}
    </div>
  )
}

function PlayerResults({ view }: { view: GameView }) {
  const { t } = useI18n()
  const results = view.results
  if (results === null) {
    return <p className="waiting-copy">{t("Checking answers…")}</p>
  }
  const own = results.player_result
  const correct = results.options.find((option) => option.option_id === results.correct_option_id)

  let verdict = t('Time’s up!')
  let tone = 'is-missed'
  if (own !== null && own.option_id !== null) {
    verdict = t(own.is_correct ? 'Correct!' : 'Not this time')
    tone = own.is_correct ? 'is-right' : 'is-wrong'
  }

  return (
    <div className="stage results-stage">
      <h2 className="question-text" lang={results.language} dir={direction(results.language)}>{results.text}</h2>
      {results.explanation && <p className="question-explanation" lang={results.language} dir={direction(results.language)}>{results.explanation}</p>}
      <div className={`verdict ${tone}`} role="status">
        <strong>{verdict}</strong>
        {own !== null && own.points_awarded > 0 && <span><bdi dir="ltr">+{own.points_awarded}</bdi>{' '}{t('points')}</span>}
      </div>
      <p className="correct-answer">{t("Correct answer:")} <strong><bdi>{correct?.text}</bdi></strong>
      </p>
      <AnswerBars options={results.options} statistics={results.statistics} ownOptionId={own?.option_id} />
      {own !== null && <p className="total-score">{t('Total: {score} points', { score: own.total_score.toLocaleString('en-US') })}</p>}
    </div>
  )
}

function PlayerFinal({ view, me, onLeave }: { view: GameView; me: Player; onLeave: () => void }) {
  const { t } = useI18n()
  const finished = view.finished
  if (finished === null) {
    return <p className="waiting-copy">{t("Final results are coming…")}</p>
  }
  const mine = finished.leaderboard.entries.find((entry) => entry.player_id === me.player_id)
  return (
    <div className="stage final-stage">
      <Winners winners={finished.winners} />
      {mine !== undefined && (
        <p className="your-place">
          {t('You finished #{rank} with {score} points', { rank: mine.rank, score: mine.total_score.toLocaleString('en-US') })}
        </p>
      )}
      <LeaderboardList entries={finished.leaderboard.entries} highlightPlayerId={me.player_id} />
      <button type="button" className="primary-button" onClick={onLeave}>{t("Play again")}</button>
    </div>
  )
}
