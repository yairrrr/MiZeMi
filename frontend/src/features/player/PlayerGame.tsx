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
  const room = view.room
  const me = room?.players.find((player) => player.player_id === session.player_id) ?? null

  if (status === 'removed' || (room !== null && me === null)) {
    return (
      <section className="game-shell player-shell">
        <div className="stage centered-stage">
          <h2>You left the room</h2>
          <p className="card-copy">The host removed you from this game.</p>
          <button type="button" className="primary-button" onClick={onLeave}>
            Back to start
          </button>
        </div>
      </section>
    )
  }

  return (
    <section className="game-shell player-shell" aria-label="Player screen">
      <header className="game-header compact">
        <div>
          <p className="eyebrow">Room {session.room_code}</p>
          <strong className="player-name">{session.display_name}</strong>
        </div>
        {me !== null && room !== null && !['LOBBY', 'PROFILE_COLLECTION', 'READY'].includes(room.state) && (
          <span className="score-pill" aria-label="Your score">
            {me.score.toLocaleString('en-US')} pts
          </span>
        )}
      </header>

      <ConnectionBanner status={status} onLeave={onLeave} />
      {view.error !== null && <ErrorToast error={view.error} onDismiss={dismissError} />}

      {room === null || me === null ? (
        <div className="stage centered-stage">
          <p className="eyebrow">You’re in, {session.display_name}!</p>
          <p className="waiting-copy">Connecting to the room…</p>
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
        <p className="waiting-copy">Get ready…</p>
      ) : (
        <PlayerQuestion key={view.question.question_id} question={view.question} view={view} send={send} connected={connected} />
      )
    case 'QUESTION_RESULTS':
      return <PlayerResults view={view} />
    case 'LEADERBOARD':
      return (
        <div className="stage leaderboard-stage">
          <h2>Leaderboard</h2>
          <LeaderboardList entries={view.leaderboard ?? []} highlightPlayerId={me.player_id} />
          <p className="waiting-copy">Waiting for the host…</p>
        </div>
      )
    case 'FINISHED':
      return <PlayerFinal view={view} me={me} onLeave={onLeave} />
  }
}

function PlayerLobby({ room, me, send }: { room: RoomSnapshot; me: Player; send: SendFn }) {
  const readyCount = room.players.filter((player) => player.is_ready).length
  if (!me.is_ready) {
    return (
      <div className="stage centered-stage">
        <span className="big-check" aria-hidden="true">✓</span>
        <h2>Profile saved!</h2>
        <p className="card-copy">Tap ready when you’re set. The game starts once everyone is ready.</p>
        <button type="button" className="primary-button join-button" onClick={() => send('player.ready')}>
          I’m ready
        </button>
      </div>
    )
  }
  return (
    <div className="stage centered-stage">
      <span className="big-check" aria-hidden="true">🎉</span>
      <h2>You’re ready!</h2>
      <p className="card-copy" aria-live="polite">
        {room.state === 'READY'
          ? 'Everyone is ready — waiting for the host to start.'
          : `${readyCount} of ${room.players.length} players ready…`}
      </p>
    </div>
  )
}

function PlayerQuestion({ question, view, send, connected }: { question: Question; view: GameView; send: SendFn; connected: boolean }) {
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
        Question {question.index + 1} of {question.total_questions}
      </p>
      <h2 className="question-text">{question.text}</h2>
      <Timer question={question} serverOffsetMs={view.serverOffsetMs} />
      <div className="option-grid player-options" role="group" aria-label="Answers">
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
            <span>{option.text}</span>
          </button>
        ))}
      </div>
      {chosen !== null && (
        <p className="answer-status" role="status">
          {locked ? 'Answer locked in!' : 'Sending…'}
          {progress !== null && ` ${progress.answered_count} of ${progress.player_count} answered.`}
        </p>
      )}
    </div>
  )
}

function PlayerResults({ view }: { view: GameView }) {
  const results = view.results
  if (results === null) {
    return <p className="waiting-copy">Checking answers…</p>
  }
  const own = results.player_result
  const correct = results.options.find((option) => option.option_id === results.correct_option_id)

  let verdict = 'Time’s up!'
  let tone = 'is-missed'
  if (own !== null && own.option_id !== null) {
    verdict = own.is_correct ? 'Correct!' : 'Not this time'
    tone = own.is_correct ? 'is-right' : 'is-wrong'
  }

  return (
    <div className="stage results-stage">
      <h2 className="question-text">{results.text}</h2>
      <div className={`verdict ${tone}`} role="status">
        <strong>{verdict}</strong>
        {own !== null && own.points_awarded > 0 && <span>+{own.points_awarded} points</span>}
      </div>
      <p className="correct-answer">
        Correct answer: <strong>{correct?.text}</strong>
      </p>
      <AnswerBars options={results.options} statistics={results.statistics} ownOptionId={own?.option_id} />
      {own !== null && <p className="total-score">Total: {own.total_score.toLocaleString('en-US')} points</p>}
    </div>
  )
}

function PlayerFinal({ view, me, onLeave }: { view: GameView; me: Player; onLeave: () => void }) {
  const finished = view.finished
  if (finished === null) {
    return <p className="waiting-copy">Final results are coming…</p>
  }
  const mine = finished.leaderboard.entries.find((entry) => entry.player_id === me.player_id)
  return (
    <div className="stage final-stage">
      <Winners winners={finished.winners} />
      {mine !== undefined && (
        <p className="your-place">
          You finished <strong>#{mine.rank}</strong> with {mine.total_score.toLocaleString('en-US')} points
        </p>
      )}
      <LeaderboardList entries={finished.leaderboard.entries} highlightPlayerId={me.player_id} />
      <button type="button" className="primary-button" onClick={onLeave}>
        Play again
      </button>
    </div>
  )
}
