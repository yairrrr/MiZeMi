export const CLIENT_TO_SERVER_EVENTS = [
  'player.join',
  'player.profile_submit',
  'player.ready',
  'game.start',
  'answer.submit',
  'game.next',
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
