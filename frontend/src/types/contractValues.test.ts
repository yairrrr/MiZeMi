import { describe, expect, test } from 'vitest'

import {
  CLIENT_TO_SERVER_EVENTS,
  ERROR_CODES,
  GAME_STATES,
  SERVER_TO_CLIENT_EVENTS,
} from './index'

describe('shared contract closed values', () => {
  test('represents the approved game states exactly', () => {
    expect(GAME_STATES).toEqual([
      'LOBBY',
      'PROFILE_COLLECTION',
      'READY',
      'QUESTION_ACTIVE',
      'QUESTION_RESULTS',
      'LEADERBOARD',
      'FINISHED',
    ])
  })

  test('represents the approved error codes exactly', () => {
    expect(ERROR_CODES).toEqual([
      'ROOM_NOT_FOUND',
      'ROOM_FULL',
      'NAME_TAKEN',
      'INVALID_STATE_TRANSITION',
      'QUESTION_CLOSED',
      'ALREADY_ANSWERED',
      'NOT_HOST',
      'VALIDATION_ERROR',
      'UNKNOWN_EVENT',
      'INTERNAL_ERROR',
      'ROOM_NOT_JOINABLE',
    ])
  })

  test('represents the approved client-to-server events exactly', () => {
    expect(CLIENT_TO_SERVER_EVENTS).toEqual([
      'player.join',
      'player.profile_submit',
      'player.ready',
      'game.start',
      'answer.submit',
      'game.next',
    ])
  })

  test('represents the approved server-to-client events exactly', () => {
    expect(SERVER_TO_CLIENT_EVENTS).toEqual([
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
    ])
  })
})
