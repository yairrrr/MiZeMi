import { useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { useStageFocus } from '../../hooks/useStageFocus'
import { useI18n, direction } from '../../i18n/I18n'
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
  const { t } = useI18n()
  const room = view.room
  const stage = !room ? 'connecting' : ['LOBBY', 'PROFILE_COLLECTION', 'READY'].includes(room.state)
    ? 'lobby' : `${room.state}-${view.question?.question_id}-${view.results?.question_id}-${!!view.finished}`
  const stageRef = useStageFocus(stage)
  return (
    <section ref={stageRef} className="game-shell host-shell" aria-label={t("Host screen")}>
      <header className="game-header">
        <div>
          <p className="eyebrow">{t("MiZeMi · Room code")}</p>
          <strong className="room-code" dir="ltr" aria-label={t('Room code {code}', { code: session.room_code })}>
            {session.room_code}
          </strong>
        </div>
        <button type="button" className="ghost-button" onClick={onLeave}>{t("Leave")}</button>
      </header>

      <ConnectionBanner status={status} onLeave={onLeave} />
      {view.error !== null && <ErrorToast error={view.error} onDismiss={dismissError} />}

      {room === null ? (
        <p className="waiting-copy">{t("Connecting to your room…")}</p>
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
      return <HostLobby room={room} send={send} error={view.error} />
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

function HostLobby({ room, send, error }: { room: RoomSnapshot; send: SendFn; error: GameView['error'] }) {
  const { t } = useI18n()
  // AI mode writes the questions on the server, which takes a while: show it,
  // and keep the button from being pressed again (the server would refuse).
  const isAi = room.config.question_source === 'ai'
  const [starting, setStarting] = useState(false)
  useEffect(() => { setStarting(false) }, [room.state, error])
  const players = room.players
  const readyCount = players.filter((player) => player.is_ready).length
  const canStart = room.state === 'READY'
  const joinUrl = `${window.location.origin}/?room=${encodeURIComponent(room.room_code)}`

  let startLabel = t('Start game')
  if (!canStart) {
    startLabel = t(players.length === 0 ? 'Waiting for players to join…' : 'Waiting for everyone to be ready…')
  }

  return (
    <div className="stage lobby-stage">
      <div className="join-instructions">
        <figure className="join-qr">
          <QRCodeSVG
            value={joinUrl}
            size={176}
            level="M"
            marginSize={0}
            fgColor="#2f2170"
            bgColor="#ffffff"
            role="img"
            aria-label={t('QR code to join room {code}', { code: room.room_code })}
          />
        </figure>
        <div className="join-copy">
          <h2>{t("Join on your phone")}</h2>
          <p className="join-scan">{t("Scan the code with your phone camera to open the room.")}</p>
          <p className="join-fallback">
            {t('No camera? Open {host} and enter the code', { host: window.location.host })}{' '}
            <bdi className="join-code" dir="ltr">{room.room_code}</bdi>
          </p>
        </div>
      </div>

      <p className="game-config-summary">{t('{count} questions · {language}', { count: room.config.question_count, language: t(room.config.language === 'he' ? 'Hebrew' : 'English') })}</p>
      <div className="lobby-summary" aria-live="polite">
        <span>
          {t('{count} joined', { count: players.length })}
        </span>
        <span>
          {t('{count} profiles', { count: players.filter((player) => player.has_profile).length })}
        </span>
        <span>
          {t('{count} ready', { count: readyCount })}
        </span>
      </div>

      <PlayerRoster
        players={players}
        onRemove={(player) => send('player.remove', { player_id: player.player_id })}
      />

      <button
        type="button"
        className="primary-button start-button"
        disabled={!canStart || starting}
        onClick={() => { if (send('game.start') && isAi) setStarting(true) }}
      >
        {starting ? t('AI is crafting your questions…') : startLabel}
      </button>
      {starting && (
        <p className="waiting-copy" role="status" aria-live="polite">
          ⚡ {t('This can take a few minutes. Everyone stays connected.')}
        </p>
      )}
    </div>
  )
}

function HostQuestion({ room, view }: { room: RoomSnapshot; view: GameView }) {
  const { t } = useI18n()
  const question = view.question
  if (question === null) {
    return <p className="waiting-copy">{t("Loading the question…")}</p>
  }
  const progress = view.progress?.question_id === question.question_id ? view.progress : null
  const answered = progress?.answered_count ?? 0
  const total = progress?.player_count ?? room.players.length

  return (
    <div className="stage question-stage">
      <p className="question-count">
        {t('Question {current} of {total}', { current: question.index + 1, total: question.total_questions })}
      </p>
      <h2 className="question-text" lang={question.language} dir={direction(question.language)}>{question.text}</h2>
      <span className="difficulty-badge">{t(question.difficulty === 'HARD' ? 'Hard' : question.difficulty === 'MEDIUM' ? 'Medium' : 'Easy')}</span>
      {room.config.question_source === 'ai' && (
        <span className="difficulty-badge ai-badge" style={{ background: '#6547cb', color: '#fff', marginInlineStart: '0.4rem' }}>⚡ {t('AI question')}</span>
      )}
      {room.config.question_count > room.total_questions && <p className="privacy-hint">{t('Only {actual} of {requested} questions could be made from the shared profiles.', { actual: room.total_questions, requested: room.config.question_count })}</p>}
      <Timer question={question} serverOffsetMs={view.serverOffsetMs} sound />
      <ol className="option-grid host-options" dir={direction(question.language)}>
        {question.options.map((option, index) => (
          <li key={option.option_id} className={`option-tile option-${index}`}>
            <span className="option-letter">{optionLetter(index)}</span>
            <bdi>{option.text}</bdi>
          </li>
        ))}
      </ol>
      <p className="answer-progress" aria-live="polite">
        {t('{answered} / {total} answered', { answered, total })}
      </p>
    </div>
  )
}

function HostResults({ view, send }: { view: GameView; send: SendFn }) {
  const { t } = useI18n()
  const results = view.results
  if (results === null) {
    return <p className="waiting-copy">{t("Tallying the answers…")}</p>
  }
  const correct = results.options.find((option) => option.option_id === results.correct_option_id)
  const { answered_count, player_count } = results.statistics

  return (
    <div className="stage results-stage">
      <h2 className="question-text" lang={results.language} dir={direction(results.language)}>{results.text}</h2>
      {results.explanation && <p className="question-explanation" lang={results.language} dir={direction(results.language)}>{results.explanation}</p>}
      <p className="correct-answer">{t("Correct answer:")} <strong><bdi>{correct?.text}</bdi></strong>
      </p>
      <AnswerBars options={results.options} statistics={results.statistics} />
      <p className="answer-progress">
        {t('{answered} of {total} players answered', { answered: answered_count, total: player_count })}
      </p>
      <button type="button" className="primary-button" onClick={() => send('game.next')}>{t("Show leaderboard")}</button>
    </div>
  )
}

function HostLeaderboard({ room, view, send }: { room: RoomSnapshot; view: GameView; send: SendFn }) {
  const { t } = useI18n()
  const entries = view.leaderboard ?? []
  const index = room.current_question_index ?? 0
  const isLast = index + 1 >= room.total_questions

  return (
    <div className="stage leaderboard-stage">
      <h2>{t("Leaderboard")}</h2>
      <p className="question-count">
        {t('After question {current} of {total}', { current: index + 1, total: room.total_questions })}
      </p>
      <LeaderboardList entries={entries} />
      <button type="button" className="primary-button" onClick={() => send('game.next')}>
        {t(isLast ? 'Show final results' : 'Next question')}
      </button>
    </div>
  )
}

function HostFinal({ view, onLeave }: { view: GameView; onLeave: () => void }) {
  const { t } = useI18n()
  const finished = view.finished
  if (finished === null) {
    return <p className="waiting-copy">{t("Calculating the final results…")}</p>
  }
  return (
    <div className="stage final-stage">
      <h2>{t("Final leaderboard")}</h2>
      <Winners winners={finished.winners} applause />
      <LeaderboardList entries={finished.leaderboard.entries} />
      <button type="button" className="primary-button" onClick={onLeave}>{t("Host a new game")}</button>
    </div>
  )
}
