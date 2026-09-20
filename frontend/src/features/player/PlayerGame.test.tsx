import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { initialGameView, type GameView } from '../../state/gameReducer'
import type { PlayerSession } from '../../state/session'
import type { Player, Question, QuestionEnded, RoomSnapshot } from '../../types'
import { PlayerGameView } from './PlayerGame'

afterEach(cleanup)

const session: PlayerSession = {
  role: 'player',
  room_code: 'K7PW3N',
  game_id: 'g1',
  player_id: 'p1',
  player_token: 'secret-token',
  display_name: 'Dana',
}

const me = (overrides: Partial<Player> = {}): Player => ({
  player_id: 'p1',
  display_name: 'Dana',
  is_host: false,
  connected: true,
  has_profile: true,
  is_ready: false,
  score: 0,
  ...overrides,
})

const room = (state: RoomSnapshot['state'], players: Player[] = [me()]): RoomSnapshot => ({
  config: { question_count: 20, language: 'en' },
  room_code: 'K7PW3N',
  state,
  players,
  current_question_index: 0,
  total_questions: 3,
})

const question: Question = {
  question_id: 'q1',
  index: 0,
  total_questions: 3,
  question_type: 'multiple_choice', difficulty: 'EASY', language: 'en',
  text: 'Whose hobby is chess?',
  options: [
    { option_id: 'a', text: 'Dana' },
    { option_id: 'b', text: 'Omer' },
  ],
  time_limit_seconds: 20,
  started_at: new Date().toISOString(),
}

function renderView(view: Partial<GameView>, send = vi.fn(() => true), status: 'open' | 'removed' = 'open') {
  render(
    <PlayerGameView
      session={session}
      view={{ ...initialGameView, ...view }}
      status={status}
      send={send}
      dismissError={vi.fn()}
      onLeave={vi.fn()}
    />,
  )
  return send
}

describe('PlayerGameView', () => {
  test('asks for a profile first', () => {
    renderView({ room: room('LOBBY', [me({ has_profile: false })]) })
    expect(screen.getByRole('heading', { name: 'Tell the group about you' })).toBeVisible()
  })

  test('offers the ready button after the profile is saved', async () => {
    const send = renderView({ room: room('PROFILE_COLLECTION') })
    await userEvent.setup().click(screen.getByRole('button', { name: 'I’m ready' }))
    expect(send).toHaveBeenCalledWith('player.ready')
  })

  test('shows the waiting state once ready', () => {
    renderView({ room: room('READY', [me({ is_ready: true })]) })
    expect(screen.getByText(/waiting for the host to start/i)).toBeVisible()
  })

  test('shows the question and submits the chosen option', async () => {
    const send = renderView({ room: room('QUESTION_ACTIVE'), question })
    expect(screen.getByRole('heading', { name: 'Whose hobby is chess?' })).toBeVisible()
    expect(screen.getByText('Question 1 of 3')).toBeVisible()

    await userEvent.setup().click(screen.getByRole('button', { name: /Omer/ }))

    expect(send).toHaveBeenCalledWith('answer.submit', { question_id: 'q1', option_id: 'b' })
    expect(screen.getByRole('button', { name: /Dana/ })).toBeDisabled()
  })

  test('locks the options once the server accepted the answer', () => {
    renderView({ room: room('QUESTION_ACTIVE'), question, answeredOptionId: 'a' })
    expect(screen.getByRole('status', { name: 'Answer status' })).toHaveTextContent('Answer locked in!')
    expect(screen.getByRole('button', { name: /Omer/ })).toBeDisabled()
  })

  test('shows the player’s own result with the correct answer', () => {
    const results: QuestionEnded = {
      difficulty: 'EASY', language: 'en',
      question_id: 'q1',
      explanation: 'Saw and The Conjuring are horror films. <img src=x onerror=alert(1)>',
      text: question.text,
      options: question.options,
      correct_option_id: 'a',
      statistics: {
        question_id: 'q1',
        correct_option_id: 'a',
        answer_distribution: [
          { option_id: 'a', count: 2, percentage: 66.7 },
          { option_id: 'b', count: 1, percentage: 33.3 },
        ],
        answered_count: 3,
        player_count: 3,
      },
      player_result: { option_id: 'a', is_correct: true, points_awarded: 842, total_score: 842 },
    }
    renderView({ room: room('QUESTION_RESULTS'), results })

    expect(screen.getByText('Correct!')).toBeVisible()
    // The signed number is isolated from surrounding RTL/LTR words.
    expect(screen.getByRole('status')).toHaveTextContent('+842 points')
    expect(screen.getByText('+842')).toHaveAttribute('dir', 'ltr')
    expect(screen.getByText(results.explanation!)).toHaveAttribute('lang', 'en')
    expect(screen.getByText(results.explanation!)).toHaveAttribute('dir', 'ltr')
    expect(document.querySelector('.question-explanation img')).toBeNull()
    expect(screen.getByLabelText('Answer distribution')).toHaveTextContent('67%')
  })

  test('highlights the player on the leaderboard', () => {
    renderView({
      room: room('LEADERBOARD'),
      leaderboard: [
        { rank: 1, player_id: 'p2', display_name: 'Omer', total_score: 1000 },
        { rank: 2, player_id: 'p1', display_name: 'Dana', total_score: 800 },
      ],
    })
    expect(within(screen.getByRole('list', { name: 'Leaderboard' })).getByText('Dana').closest('li')).toHaveClass('is-me')
  })

  test('shows the winner and the player’s final place', () => {
    const entries = [
      { rank: 1, player_id: 'p2', display_name: 'Omer', total_score: 1000 },
      { rank: 2, player_id: 'p1', display_name: 'Dana', total_score: 800 },
    ]
    renderView({ room: room('FINISHED'), finished: { leaderboard: { entries }, winners: [entries[0]] } })

    expect(screen.getByRole('status')).toHaveTextContent('Omer')
    expect(screen.getByText(/You finished/)).toHaveTextContent('#2')
  })

  test('shows a clear screen when removed by the host', () => {
    renderView({ room: room('LOBBY', []) })
    expect(screen.getByRole('heading', { name: 'You left the room' })).toBeVisible()
  })

  test('never renders the player token', () => {
    renderView({ room: room('LOBBY') })
    expect(document.body.textContent).not.toContain('secret-token')
  })
})

 test('allows an unacknowledged answer to be retried after reconnect', async () => {
  const props = { session, view: { ...initialGameView, room: room('QUESTION_ACTIVE'), question },
    send: vi.fn(() => true), dismissError: vi.fn(), onLeave: vi.fn() }
  const { rerender } = render(<PlayerGameView {...props} status="open" />)
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: /Omer/ }))
  expect(screen.getByRole('status', { name: 'Answer status' })).toHaveTextContent('Sending…')
  rerender(<PlayerGameView {...props} status="reconnecting" />)
  expect(screen.getByRole('button', { name: /Omer/ })).toBeDisabled()
  rerender(<PlayerGameView {...props} status="open" />)
  await user.click(screen.getByRole('button', { name: /Omer/ }))
  expect(props.send).toHaveBeenCalledTimes(2)
 })

vi.mock('../../legal/privacyInfo', () => ({ usePrivacyInfo: () => ({
  info: { policy_version: '2026-09-18', retention_days: 7, room_idle_ttl_minutes: 120,
    maintenance_interval_seconds: 300, raw_profiles_persisted: false },
  status: 'ready', retry: () => {},
}) }))
