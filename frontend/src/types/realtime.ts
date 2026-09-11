import type {
  AnswerAccepted,
  AnswerProgress,
  ErrorResponse,
  GameFinished,
  GameStarted,
  Leaderboard,
  Question,
  QuestionEnded,
  RoomSnapshot,
} from './contracts'

export const CLIENT_TO_SERVER_EVENTS = [
  'player.join',
  'player.profile_submit',
  'player.ready',
  'game.start',
  'answer.submit',
  'game.next',
  'player.remove',
] as const

export type ClientToServerEvent = (typeof CLIENT_TO_SERVER_EVENTS)[number]

export const SERVER_TO_CLIENT_EVENTS = [
  'room.updated',
  'player.joined',
  'player.updated',
  'game.started',
  'question.started',
  'answer.accepted',
  'question.ended',
  'statistics.updated',
  'leaderboard.updated',
  'game.finished',
  'error',
] as const

export type ServerToClientEvent = (typeof SERVER_TO_CLIENT_EVENTS)[number]

export type WebSocketEnvelope<TEvent extends string, TPayload> = {
  event: TEvent
  payload: TPayload
  timestamp: string
  game_id: string
}

/** Every server message the app acts on, discriminated by ``event`` (§14.2). */
export type ServerMessage =
  | WebSocketEnvelope<'room.updated', RoomSnapshot>
  | WebSocketEnvelope<'game.started', GameStarted>
  | WebSocketEnvelope<'question.started', Question>
  | WebSocketEnvelope<'answer.accepted', AnswerAccepted>
  | WebSocketEnvelope<'statistics.updated', AnswerProgress>
  | WebSocketEnvelope<'question.ended', QuestionEnded>
  | WebSocketEnvelope<'leaderboard.updated', Leaderboard>
  | WebSocketEnvelope<'game.finished', GameFinished>
  | WebSocketEnvelope<'error', ErrorResponse>
