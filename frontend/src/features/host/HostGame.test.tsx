import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QRCodeSVG } from 'qrcode.react'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { initialGameView, type GameView } from '../../state/gameReducer'
import type { HostSession } from '../../state/session'
import type { Player, Question, QuestionEnded, RoomSnapshot } from '../../types'
import { HostGameView } from './HostGame'

afterEach(cleanup)

const session: HostSession = { role: 'host', room_code: 'K7PW3N', game_id: 'g1', host_token: 'host-secret' }

const player = (id: string, name: string, overrides: Partial<Player> = {}): Player => ({
  player_id: id,
  display_name: name,
  is_host: false,
  connected: true,
  has_profile: true,
  is_ready: true,
  score: 0,
  ...overrides,
})

const room = (state: RoomSnapshot['state'], players: Player[], index: number | null = 0): RoomSnapshot => ({
  config: { question_count: 20, language: 'en', question_source: 'algorithmic' },
  room_code: 'K7PW3N',
  state,
  players,
  current_question_index: index,
  total_questions: 2,
})

const question: Question = {
  question_id: 'q1',
  index: 0,
  total_questions: 2,
  question_type: 'multiple_choice', difficulty: 'EASY', language: 'en',
  text: 'What is the most common favorite food?',
  options: [
    { option_id: 'a', text: 'pizza' },
    { option_id: 'b', text: 'sushi' },
  ],
  time_limit_seconds: 20,
  started_at: new Date().toISOString(),
}

function renderView(view: Partial<GameView>, send = vi.fn(() => true)) {
  render(
    <HostGameView
      session={session}
      view={{ ...initialGameView, ...view }}
      status="open"
      send={send}
      dismissError={vi.fn()}
      onLeave={vi.fn()}
    />,
  )
  return send
}

describe('HostGameView', () => {
  test('shows the room code prominently', () => {
    renderView({})
    expect(screen.getByLabelText('Room code K7PW3N')).toHaveTextContent('K7PW3N')
  })

  test('shows a scannable QR code that opens this room instead of a raw link', () => {
    renderView({ room: room('LOBBY', []) })
    const qr = screen.getByRole('img', { name: 'QR code to join room K7PW3N' })
    const expected = render(<QRCodeSVG value={`${window.location.origin}/?room=K7PW3N`} level="M" marginSize={0} />)
    const modules = (svg: Element) => svg.querySelectorAll('path')[1]?.getAttribute('d')
    expect(modules(qr)).toMatch(/^M/)
    expect(modules(qr)).toBe(modules(expected.container.querySelector('svg')!))
    expect(screen.queryByText(`${window.location.origin}/?room=K7PW3N`)).toBeNull()
  })

  test('lists players with profile and readiness status', () => {
    renderView({
      room: room('PROFILE_COLLECTION', [
        player('p1', 'Dana'),
        player('p2', 'Omer', { has_profile: false, is_ready: false, connected: false }),
      ]),
    })
    const roster = screen.getByRole('list', { name: 'Players' })
    expect(roster).toHaveTextContent('Dana')
    expect(roster).toHaveTextContent('Profile…')
    expect(screen.getAllByText('Disconnected', { exact: true })).toHaveLength(1)
  })

  test('start is disabled until everyone is ready', () => {
    renderView({ room: room('PROFILE_COLLECTION', [player('p1', 'Dana', { is_ready: false })]) })
    expect(screen.getByRole('button', { name: /waiting for everyone/i })).toBeDisabled()
  })

  test('starts the game when the room is ready', async () => {
    const send = renderView({ room: room('READY', [player('p1', 'Dana')]) })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Start game' }))
    expect(send).toHaveBeenCalledWith('game.start')
  })

  test('can remove a player before the game', async () => {
    const send = renderView({ room: room('LOBBY', [player('p1', 'Dana')]) })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Remove Dana' }))
    expect(send).toHaveBeenCalledWith('player.remove', { player_id: 'p1' })
  })

  test('shows the live question with answer progress', () => {
    renderView({
      room: room('QUESTION_ACTIVE', [player('p1', 'Dana'), player('p2', 'Omer')]),
      question,
      progress: { question_id: 'q1', answered_count: 1, player_count: 2 },
    })
    expect(screen.getByRole('heading', { name: question.text })).toBeVisible()
    expect(screen.getByText('1 / 2 answered')).toBeVisible()
    expect(screen.getByRole('timer')).toBeVisible()
  })

  test('shows results with the correct answer and moves to the leaderboard', async () => {
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
          { option_id: 'a', count: 3, percentage: 75 },
          { option_id: 'b', count: 1, percentage: 25 },
        ],
        answered_count: 4,
        player_count: 4,
      },
      player_result: null,
    }
    const send = renderView({ room: room('QUESTION_RESULTS', []), results })

    expect(screen.getByText('Correct answer:')).toHaveTextContent('pizza')
    expect(screen.getByText(results.explanation!)).toHaveAttribute('lang', 'en')
    expect(screen.getByText(results.explanation!)).toHaveAttribute('dir', 'ltr')
    expect(document.querySelector('.question-explanation img')).toBeNull()
    expect(screen.getByLabelText('Answer distribution')).toHaveTextContent('75%')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Show leaderboard' }))
    expect(send).toHaveBeenCalledWith('game.next')
  })

  test('offers the next question, then the final results', () => {
    const entries = [{ rank: 1, player_id: 'p1', display_name: 'Dana', total_score: 900 }]
    renderView({ room: room('LEADERBOARD', [player('p1', 'Dana')], 0), leaderboard: entries })
    expect(screen.getByRole('button', { name: 'Next question' })).toBeVisible()
    cleanup()

    renderView({ room: room('LEADERBOARD', [player('p1', 'Dana')], 1), leaderboard: entries })
    expect(screen.getByRole('button', { name: 'Show final results' })).toBeVisible()
  })

  test('a shorter game than requested shows and ends at its actual total', () => {
    // 20 requested; the engine made 2 rather than repeat an answer.
    const last: Question = { ...question, question_id: 'q2', index: 1 }
    renderView({ room: room('QUESTION_ACTIVE', [player('p1', 'Dana')], 1), question: last })
    expect(screen.getByText('Question 2 of 2')).toBeVisible()
    expect(screen.getByText('Only 2 of 20 questions could be made from the shared profiles.')).toBeVisible()
    cleanup()

    const entries = [{ rank: 1, player_id: 'p1', display_name: 'Dana', total_score: 900 }]
    renderView({ room: room('LEADERBOARD', [player('p1', 'Dana')], 1), leaderboard: entries })
    expect(screen.getByText('After question 2 of 2')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Show final results' })).toBeVisible()
  })

  test('celebrates co-winners on a tie', () => {
    const entries = [
      { rank: 1, player_id: 'p1', display_name: 'Dana', total_score: 900 },
      { rank: 1, player_id: 'p2', display_name: 'Omer', total_score: 900 },
    ]
    renderView({ room: room('FINISHED', []), finished: { leaderboard: { entries }, winners: entries } })
    expect(screen.getByRole('status')).toHaveTextContent("It's a tie!")
    expect(screen.getByRole('status')).toHaveTextContent('Dana & Omer')
  })

  test('shows server errors such as missing question data', () => {
    renderView({
      room: room('READY', [player('p1', 'Dana')]),
      error: { code: 'NO_QUESTIONS_AVAILABLE', message: "We couldn't build any questions from the profiles yet." },
    })
    expect(screen.getByRole('alert')).toHaveTextContent("We couldn't build any questions")
  })

  test('never renders the host token', () => {
    renderView({ room: room('LOBBY', []) })
    expect(document.body.textContent).not.toContain('host-secret')
  })
})
