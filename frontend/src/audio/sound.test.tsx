import { act, cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import * as sound from './sound'
import { SoundToggle } from './SoundToggle'
import { Timer, Winners } from '../components/GameParts'
import type { Question } from '../types'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.useRealTimers()
  sound.setMuted(false)
})

describe('sound engine', () => {
  test('stays silent and never throws without Web Audio (jsdom)', () => {
    expect(() => {
      sound.unlockAudio()
      sound.playClick()
      sound.playTick(true)
      sound.playTimeUp()
      sound.playApplause()
    }).not.toThrow()
  })

  test('remembers the mute choice on this device', () => {
    sound.setMuted(true)
    expect(sound.isMuted()).toBe(true)
    expect(window.localStorage.getItem('mizemi.sound')).toBe('off')
    sound.setMuted(false)
    expect(window.localStorage.getItem('mizemi.sound')).toBe('on')
  })

  test('the header toggle mutes and unmutes', async () => {
    const user = userEvent.setup()
    render(<SoundToggle />)
    const toggle = screen.getByRole('button', { name: 'Sound on — turn sound off' })
    expect(toggle).toHaveAttribute('aria-pressed', 'true')

    await user.click(toggle)

    expect(sound.isMuted()).toBe(true)
    expect(screen.getByRole('button', { name: 'Sound off — turn sound on' })).toHaveAttribute('aria-pressed', 'false')
  })
})

describe('game sounds', () => {
  const now = Date.UTC(2026, 9, 5, 12)
  const question: Question = { question_id: 'q', index: 0, total_questions: 1,
    question_type: 'multiple_choice', difficulty: 'EASY', language: 'en', text: 'Synthetic?',
    options: [{ option_id: 'a', text: 'A' }, { option_id: 'b', text: 'B' }],
    time_limit_seconds: 8, started_at: new Date(now).toISOString() }

  test('the host timer ticks once per second, urgently near the end, then chimes', () => {
    vi.useFakeTimers()
    vi.setSystemTime(now)
    const tick = vi.spyOn(sound, 'playTick').mockImplementation(() => {})
    const timeUp = vi.spyOn(sound, 'playTimeUp').mockImplementation(() => {})
    render(<Timer question={question} serverOffsetMs={0} sound />)

    for (let second = 0; second < 8; second++) act(() => vi.advanceTimersByTime(1_000))

    expect(tick.mock.calls.map(([urgent]) => urgent)).toEqual([false, false, false, true, true, true, true, true])
    expect(timeUp).toHaveBeenCalledOnce()
  })

  test('a timer without sound stays quiet', () => {
    vi.useFakeTimers()
    vi.setSystemTime(now)
    const tick = vi.spyOn(sound, 'playTick').mockImplementation(() => {})
    render(<Timer question={question} serverOffsetMs={0} />)
    act(() => vi.advanceTimersByTime(8_000))
    expect(tick).not.toHaveBeenCalled()
  })

  test('applause plays once when the winner is shown, and only where asked', () => {
    const applause = vi.spyOn(sound, 'playApplause').mockImplementation(() => {})
    const winner = { player_id: 'p', display_name: 'Dana', rank: 1, total_score: 900 }
    const { rerender } = render(<Winners winners={[winner]} applause />)
    rerender(<Winners winners={[winner]} applause />)
    render(<Winners winners={[winner]} />)
    expect(applause).toHaveBeenCalledOnce()
  })
})
