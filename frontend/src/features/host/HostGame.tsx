import {
  AnswerBars,
  ConnectionBanner,
  ErrorToast,
  LeaderboardList,
  optionLetter,
  PlayerRoster,
  Timer,
  Winners,
} from '../../components/GameParts'
import { type SendFn, useGameConnection } from '../../hooks/useGameConnection'
import type { SocketStatus } from '../../realtime/gameSocket'
import type { GameView } from '../../state/gameReducer'
import type { HostSession } from '../../state/session'
import type { RoomSnapshot } from '../../types'

type HostGameViewProps = {
  session: HostSession
  view: GameView
  status: SocketStatus
  send: SendFn
  dismissError: () => void
  onLeave: () => void
}

export function HostGame({ session, onLeave }: { session: HostSession; onLeave: () => void }) {
  const connection = useGameConnection(session)
  return <HostGameView session={session} onLeave={onLeave} {...connection} />
}

export function HostGameView({ session, view, status, send, dismissError, onLeave }: HostGameViewProps) {
  const room = view.room
  return (
    <section className="game-shell host-shell" aria-label="Host screen">
      <header className="game-header">
        <div>
          <p className="eyebrow">MiZeMi · Room code</p>
          <strong className="room-code" aria-label={`Room code ${session.room_code}`}>
            {session.room_code}
          </strong>
        </div>
        <button type="button" className="ghost-button" onClick={onLeave}>
          Leave
        </button>
      </header>

      <ConnectionBanner status={status} onLeave={onLeave} />
      {view.error !== null && <ErrorToast error={view.error} onDismiss={dismissError} />}

      {room === null ? (
        <p className="waiting-copy">Connecting to your room…</p>
      ) : (
        <fieldset className="stage-controls" disabled={status !== 'open'}>
          <HostStage room={room} view={view} send={send} onLeave={onLeave} />
        </fieldset>
      )}
    </section>
  )
}

function HostStage({
  room,
  view,
  send,
  onLeave,
}: {
  room: RoomSnapshot
  view: GameView
  send: SendFn
  onLeave: () => void
}) {
  switch (room.state) {
    case 'LOBBY':
    case 'PROFILE_COLLECTION':
    case 'READY':
      return <HostLobby room={room} send={send} />
    case 'QUESTION_ACTIVE':
      return <HostQuestion room={room} view={view} />
    case 'QUESTION_RESULTS':
      return <HostResults view={view} send={send} />
    case 'LEADERBOARD':
      return <HostLeaderboard room={room} view={view} send={send} />
    case 'FINISHED':
      return <HostFinal view={view} onLeave={onLeave} />
  }
}

function HostLobby({ room, send }: { room: RoomSnapshot; send: SendFn }) {
  const players = room.players
  const readyCount = players.filter((player) => player.is_ready).length
  const canStart = room.state === 'READY'
  const joinUrl = `${window.location.origin}/?room=${room.room_code}`

  let startLabel = 'Start game'
  if (!canStart) {
    startLabel = players.length === 0 ? 'Waiting for players to join…' : 'Waiting for everyone to be ready…'
  }

  return (
    <div className="stage lobby-stage">
      <div className="join-instructions">
        <h2>Join on your phone</h2>
        <p>
          Open <strong>{window.location.host}</strong> and enter the room code — or use{' '}
          <span className="join-link">{joinUrl}</span>
        </p>
      </div>

      <div className="lobby-summary" aria-live="polite">
        <span>
          <strong>{players.length}</strong> joined
        </span>
        <span>
          <strong>{players.filter((player) => player.has_profile).length}</strong> profiles
        </span>
        <span>
          <strong>{readyCount}</strong> ready
        </span>
      </div>

      <PlayerRoster
        players={players}
        onRemove={(player) => send('player.remove', { player_id: player.player_id })}
      />

      <button
        type="button"
        className="primary-button start-button"
        disabled={!canStart}
        onClick={() => send('game.start')}
      >
        {startLabel}
      </button>
    </div>
  )
}

function HostQuestion({ room, view }: { room: RoomSnapshot; view: GameView }) {
  const question = view.question
  if (question === null) {
    return <p className="waiting-copy">Loading the question…</p>
  }
  const progress = view.progress?.question_id === question.question_id ? view.progress : null
  const answered = progress?.answered_count ?? 0
  const total = progress?.player_count ?? room.players.length

  return (
    <div className="stage question-stage">
      <p className="question-count">
        Question {question.index + 1} of {question.total_questions}
      </p>
      <h2 className="question-text">{question.text}</h2>
      <Timer question={question} serverOffsetMs={view.serverOffsetMs} />
      <ol className="option-grid host-options">
        {question.options.map((option, index) => (
          <li key={option.option_id} className={`option-tile option-${index}`}>
            <span className="option-letter">{optionLetter(index)}</span>
            <span>{option.text}</span>
          </li>
        ))}
      </ol>
      <p className="answer-progress" aria-live="polite">
        {answered} / {total} answered
      </p>
    </div>
  )
}

function HostResults({ view, send }: { view: GameView; send: SendFn }) {
  const results = view.results
  if (results === null) {
    return <p className="waiting-copy">Tallying the answers…</p>
  }
  const correct = results.options.find((option) => option.option_id === results.correct_option_id)
  const { answered_count, player_count } = results.statistics

  return (
    <div className="stage results-stage">
      <h2 className="question-text">{results.text}</h2>
      <p className="correct-answer">
        Correct answer: <strong>{correct?.text}</strong>
      </p>
      <AnswerBars options={results.options} statistics={results.statistics} />
      <p className="answer-progress">
        {answered_count} of {player_count} players answered
      </p>
      <button type="button" className="primary-button" onClick={() => send('game.next')}>
        Show leaderboard
      </button>
    </div>
  )
}

function HostLeaderboard({ room, view, send }: { room: RoomSnapshot; view: GameView; send: SendFn }) {
  const entries = view.leaderboard ?? []
  const index = room.current_question_index ?? 0
  const isLast = index + 1 >= room.total_questions

  return (
    <div className="stage leaderboard-stage">
      <h2>Leaderboard</h2>
      <p className="question-count">
        After question {index + 1} of {room.total_questions}
      </p>
      <LeaderboardList entries={entries} />
      <button type="button" className="primary-button" onClick={() => send('game.next')}>
        {isLast ? 'Show final results' : 'Next question'}
      </button>
    </div>
  )
}

function HostFinal({ view, onLeave }: { view: GameView; onLeave: () => void }) {
  const finished = view.finished
  if (finished === null) {
    return <p className="waiting-copy">Calculating the final results…</p>
  }
  return (
    <div className="stage final-stage">
      <Winners winners={finished.winners} />
      <h2>Final leaderboard</h2>
      <LeaderboardList entries={finished.leaderboard.entries} />
      <button type="button" className="primary-button" onClick={onLeave}>
        Host a new game
      </button>
    </div>
  )
}
