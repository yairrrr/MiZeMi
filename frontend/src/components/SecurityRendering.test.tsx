import { cleanup, render } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { HostGameView } from '../features/host/HostGame'
import { PlayerGameView } from '../features/player/PlayerGame'
import { initialGameView, type GameView } from '../state/gameReducer'
import type { Question, QuestionEnded, RoomSnapshot } from '../types'

afterEach(cleanup)

const payloads = ['<script>alert(1)</script>', '<img src=x onerror=alert(1)>', '"><svg/onload=alert(1)>', 'דנה Dana \u202e mixed', 'א'.repeat(300)]
for (const role of ['host', 'player'] as const) {
  for (const state of ['READY', 'QUESTION_ACTIVE', 'QUESTION_RESULTS', 'LEADERBOARD', 'FINISHED'] as const) {
    test.each(payloads)(`${role} ${state} renders hostile strings as text: %s`, (text) => {
      const room: RoomSnapshot = { room_code: 'AUDIT1', state, current_question_index: 0,
        config: { question_count: 1, language: 'en', question_source: 'algorithmic' }, total_questions: 1,
        players: [{ player_id: 'p1', display_name: text, is_host: false, connected: true, has_profile: true, is_ready: true, score: 500 }] }
      const question: Question = { question_id: 'q1', index: 0, total_questions: 1,
        question_type: 'multiple_choice', difficulty: 'EASY', language: 'en', text,
        options: [{ option_id: 'a', text }, { option_id: 'b', text: 'Other answer' }],
        started_at: new Date().toISOString(), time_limit_seconds: 20 }
      const results: QuestionEnded = { question_id: 'q1', text, explanation: text,
        difficulty: 'EASY', language: 'en', options: question.options, correct_option_id: 'a',
        statistics: { question_id: 'q1', correct_option_id: 'a', answered_count: 1, player_count: 1,
          answer_distribution: [{ option_id: 'a', count: 1, percentage: 100 }] },
        player_result: { option_id: 'a', is_correct: true, points_awarded: 500, total_score: 500 } }
      const entries = [{ rank: 1, player_id: 'p1', display_name: text, total_score: 500 }]
      const view: GameView = { ...initialGameView, room, question, results, leaderboard: entries,
        finished: state === 'FINISHED' ? { leaderboard: { entries }, winners: entries } : null }
      const props = { view, status: 'open' as const, send: vi.fn(() => true), dismissError: vi.fn(), onLeave: vi.fn() }
      const { container } = render(role === 'host'
        ? <HostGameView {...props} session={{ role, room_code: 'AUDIT1', game_id: 'g1', host_token: 'synthetic-host' }} />
        : <PlayerGameView {...props} session={{ role, room_code: 'AUDIT1', game_id: 'g1', player_id: 'p1', player_token: 'synthetic-player', display_name: text }} />)
      expect(container.querySelector('script, [onerror], [onload], img[src="x"]')).toBeNull()
      // The only SVG allowed is the host's join QR code; anything else would be injected markup.
      expect([...container.querySelectorAll('svg')].filter((svg) => !svg.closest('.join-qr'))).toEqual([])
      if (!(role === 'player' && state === 'READY')) expect(container.textContent).toContain(text)
    })
  }
}
