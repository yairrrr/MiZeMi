import { describe, expect, test } from 'vitest'

import type { Question, RoomSnapshot, ServerMessage } from '../types'
import { gameReducer, initialGameView, remainingMs, type GameView } from './gameReducer'

const STAMP = '2026-09-11T10:00:00.000Z'

function msg<M extends ServerMessage>(event: M['event'], payload: M['payload'], timestamp = STAMP): ServerMessage {
  return { event, payload, timestamp, game_id: 'g1' } as ServerMessage
}

function apply(view: GameView, message: ServerMessage, receivedAt = Date.parse(STAMP)): GameView {
  return gameReducer(view, { type: 'message', message, receivedAt })
}

const room = (state: RoomSnapshot['state']): RoomSnapshot => ({
  config: { question_count: 20, language: 'en' },
  room_code: 'K7PW3N',
  state,
  players: [],
  current_question_index: state === 'LOBBY' ? null : 0,
  total_questions: 2,
})

const question: Question = {
  question_id: 'q1',
  index: 0,
  total_questions: 2,
  question_type: 'multiple_choice', difficulty: 'EASY', language: 'en',
  text: 'Who is the only player from Haifa?',
  options: [
    { option_id: 'a', text: 'Dana' },
    { option_id: 'b', text: 'Omer' },
  ],
  time_limit_seconds: 20,
  started_at: STAMP,
}

describe('gameReducer', () => {
  test('stores the authoritative room snapshot', () => {
    const view = apply(initialGameView, msg('room.updated', room('LOBBY')))
    expect(view.room?.room_code).toBe('K7PW3N')
  })

  test('question.started sets the active question and clears the old answer', () => {
    let view = apply(initialGameView, msg('question.started', question))
    view = apply(view, msg('answer.accepted', { question_id: 'q1', option_id: 'a' }))
    expect(view.answeredOptionId).toBe('a')

    view = apply(view, msg('question.started', { ...question, question_id: 'q2', index: 1 }))
    expect(view.question?.question_id).toBe('q2')
    expect(view.answeredOptionId).toBeNull()
  })

  test('a replayed question.started keeps the accepted answer (reconnect)', () => {
    let view = apply(initialGameView, msg('question.started', question))
    view = apply(view, msg('answer.accepted', { question_id: 'q1', option_id: 'b' }))
    view = apply(view, msg('question.started', question))
    expect(view.answeredOptionId).toBe('b')
  })

  test('answer.accepted for another question is ignored', () => {
    let view = apply(initialGameView, msg('question.started', question))
    view = apply(view, msg('answer.accepted', { question_id: 'other', option_id: 'a' }))
    expect(view.answeredOptionId).toBeNull()
  })

  test('tracks progress, results, leaderboard and the final result', () => {
    let view = apply(initialGameView, msg('statistics.updated', { question_id: 'q1', answered_count: 2, player_count: 3 }))
    expect(view.progress?.answered_count).toBe(2)

    const ended = {
      difficulty: 'EASY' as const, language: 'en' as const,
      question_id: 'q1',
      text: question.text,
      options: question.options,
      correct_option_id: 'b',
      statistics: {
        question_id: 'q1',
        correct_option_id: 'b',
        answer_distribution: [
          { option_id: 'a', count: 1, percentage: 33.3 },
          { option_id: 'b', count: 2, percentage: 66.7 },
        ],
        answered_count: 3,
        player_count: 3,
      },
      player_result: null,
    }
    view = apply(view, msg('question.ended', ended))
    expect(view.results?.correct_option_id).toBe('b')

    const entries = [{ rank: 1, player_id: 'p1', display_name: 'Dana', total_score: 900 }]
    view = apply(view, msg('leaderboard.updated', { entries }))
    expect(view.leaderboard).toEqual(entries)

    view = apply(view, msg('game.finished', { leaderboard: { entries }, winners: entries }))
    expect(view.finished?.winners[0].display_name).toBe('Dana')
  })

  test('returning to a pre-game state clears gameplay state', () => {
    let view = apply(initialGameView, msg('question.started', question))
    view = apply(view, msg('room.updated', room('READY')))
    expect(view.question).toBeNull()
  })

  test('errors are shown until dismissed', () => {
    let view = apply(initialGameView, msg('error', { error: { code: 'NOT_HOST', message: 'Only the host can do that.' } }))
    expect(view.error?.code).toBe('NOT_HOST')
    view = gameReducer(view, { type: 'dismissError' })
    expect(view.error).toBeNull()
  })

  test('estimates the server clock offset from envelope timestamps', () => {
    const view = apply(initialGameView, msg('room.updated', room('LOBBY')), Date.parse(STAMP) - 2_000)
    expect(view.serverOffsetMs).toBe(2_000)
  })
})

describe('remainingMs', () => {
  test('a new question cannot briefly display more than its time limit', () => {
    const start = Date.parse(STAMP)
    expect(remainingMs(question, 0, start - 250)).toBe(20_000)
    expect(remainingMs(question, -1_000, start)).toBe(20_000)
  })

  test('counts down to started_at + time limit using server time', () => {
    const start = Date.parse(STAMP)
    expect(remainingMs(question, 0, start + 5_000)).toBe(15_000)
    expect(remainingMs(question, 3_000, start + 5_000)).toBe(12_000)
    expect(remainingMs(question, 0, start + 60_000)).toBe(0)
  })
})
