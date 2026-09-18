import { act, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { Timer } from './GameParts'
import type { Question } from '../types'
afterEach(() => vi.useRealTimers())
test('announces one near-deadline warning, not each timer tick', () => {
  vi.useFakeTimers()
  const now = Date.now()
  vi.setSystemTime(now)
  const question: Question = { question_id: 'timer', index: 0, total_questions: 1,
    question_type: 'multiple_choice', difficulty: 'EASY', language: 'en', text: 'Synthetic?',
    options: [{ option_id: 'a', text: 'A' }, { option_id: 'b', text: 'B' }],
    time_limit_seconds: 20, started_at: new Date(now).toISOString() }
  render(<Timer question={question} serverOffsetMs={0} />)
  const warning = screen.getByRole('status', { name: 'Time warning' })
  expect(screen.getByRole('timer')).toHaveAttribute('aria-live', 'off')
  expect(warning).toBeEmptyDOMElement()
  act(() => vi.advanceTimersByTime(15_000))
  expect(warning).toHaveTextContent('Five seconds or less remain.')
  act(() => vi.advanceTimersByTime(4_000))
  expect(warning).toHaveTextContent('Five seconds or less remain.')
  act(() => vi.advanceTimersByTime(1_000))
  expect(warning).toHaveTextContent('Time is up.')
})
