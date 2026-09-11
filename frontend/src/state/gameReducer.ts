import type {
  AnswerProgress,
  ErrorResponse,
  GameFinished,
  LeaderboardEntry,
  Question,
  QuestionEnded,
  RoomSnapshot,
  ServerMessage,
} from '../types'

/** Everything a screen needs, derived only from server messages (§5). */
export type GameView = {
  room: RoomSnapshot | null
  question: Question | null
  /** Own accepted answer for the active question (players only). */
  answeredOptionId: string | null
  progress: AnswerProgress | null
  results: QuestionEnded | null
  leaderboard: LeaderboardEntry[] | null
  finished: GameFinished | null
  error: ErrorResponse['error'] | null
  /** server clock − client clock, estimated from envelope timestamps (ms). */
  serverOffsetMs: number
}

export type GameAction =
  | { type: 'message'; message: ServerMessage; receivedAt: number }
  | { type: 'dismissError' }

export const initialGameView: GameView = {
  room: null,
  question: null,
  answeredOptionId: null,
  progress: null,
  results: null,
  leaderboard: null,
  finished: null,
  error: null,
  serverOffsetMs: 0,
}

const PRE_GAME_STATES = new Set(['LOBBY', 'PROFILE_COLLECTION', 'READY'])

function offsetFrom(timestamp: string, receivedAt: number, previous: number): number {
  const serverTime = Date.parse(timestamp)
  return Number.isNaN(serverTime) ? previous : serverTime - receivedAt
}

export function gameReducer(view: GameView, action: GameAction): GameView {
  if (action.type === 'dismissError') {
    return { ...view, error: null }
  }

  const { message, receivedAt } = action
  const serverOffsetMs = offsetFrom(message.timestamp, receivedAt, view.serverOffsetMs)
  const next = { ...view, serverOffsetMs }

  switch (message.event) {
    case 'room.updated': {
      const room = message.payload
      if (PRE_GAME_STATES.has(room.state)) {
        return {
          ...next,
          room,
          question: null,
          answeredOptionId: null,
          progress: null,
          results: null,
          leaderboard: null,
          finished: null,
        }
      }
      return { ...next, room }
    }
    case 'game.started':
      return { ...next, results: null, leaderboard: null, finished: null }
    case 'question.started': {
      const isSameQuestion = view.question?.question_id === message.payload.question_id
      return {
        ...next,
        question: message.payload,
        answeredOptionId: isSameQuestion ? view.answeredOptionId : null,
        progress: isSameQuestion ? view.progress : null,
        results: null,
        error: null,
      }
    }
    case 'answer.accepted':
      if (view.question?.question_id !== message.payload.question_id) {
        return next
      }
      return { ...next, answeredOptionId: message.payload.option_id }
    case 'statistics.updated':
      return { ...next, progress: message.payload }
    case 'question.ended':
      return { ...next, results: message.payload }
    case 'leaderboard.updated':
      return { ...next, leaderboard: message.payload.entries }
    case 'game.finished':
      return {
        ...next,
        finished: message.payload,
        leaderboard: message.payload.leaderboard.entries,
      }
    case 'error':
      return { ...next, error: message.payload.error }
    default:
      return next
  }
}

/** Milliseconds left on the active question, using server-corrected time. */
export function remainingMs(question: Question, serverOffsetMs: number, now: number): number {
  const deadline = Date.parse(question.started_at) + question.time_limit_seconds * 1000
  // A new round can render just before the next 250ms UI clock tick.
  return Math.min(question.time_limit_seconds * 1000, Math.max(0, deadline - (now + serverOffsetMs)))
}
