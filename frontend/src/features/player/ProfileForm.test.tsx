import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { ProfileForm } from './ProfileForm'
import { buildProfileFields, initialConsent, PRIVACY_MESSAGE } from './profileSchema'

afterEach(cleanup)

async function fillRequired(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('City'), 'Haifa')
  await user.type(screen.getByLabelText('Favorite food'), 'pizza')
  await user.type(screen.getByLabelText('Hobby'), 'chess')
  await user.selectOptions(screen.getByLabelText('Favorite music style'), 'Rock')
}

describe('ProfileForm', () => {
  test('submits the approved field shape for the connected player', async () => {
    const send = vi.fn(() => true)
    const user = userEvent.setup()
    render(<ProfileForm playerId="p1" displayName="Dana" send={send} serverError={null} />)

    await fillRequired(user)
    await user.type(screen.getByLabelText('Age (optional)'), '27')
    await user.click(screen.getByRole('button', { name: 'Save my profile' }))

    expect(send).toHaveBeenCalledWith('player.profile_submit', {
      player_id: 'p1',
      fields: [
        { field_key: 'city', value: 'Haifa', allow_question_usage: true },
        { field_key: 'favorite_food', value: 'pizza', allow_question_usage: true },
        { field_key: 'hobby', value: 'chess', allow_question_usage: true },
        { field_key: 'favorite_music', value: 'Rock', allow_question_usage: true },
        { field_key: 'age', value: 27, allow_question_usage: true },
      ],
    })
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
  })

  test('the personal fact is not used in questions unless the player opts in', () => {
    render(<ProfileForm playerId="p1" displayName="Dana" send={vi.fn()} serverError={null} />)

    expect(screen.getByLabelText('Allow Something interesting about me to be used for game questions')).not.toBeChecked()
    expect(screen.getByLabelText('Allow City to be used for game questions')).toBeChecked()
  })

  test('players can withhold any field from questions', async () => {
    const send = vi.fn((_event: string, _payload?: unknown) => true)
    const user = userEvent.setup()
    render(<ProfileForm playerId="p1" displayName="Dana" send={send} serverError={null} />)

    await fillRequired(user)
    await user.click(screen.getByLabelText('Allow City to be used for game questions'))
    await user.click(screen.getByRole('button', { name: 'Save my profile' }))

    const payload = send.mock.calls[0][1] as { fields: { field_key: string; allow_question_usage: boolean }[] }
    expect(payload.fields.find((f) => f.field_key === 'city')?.allow_question_usage).toBe(false)
  })

  test('shows a validation message and does not send an incomplete profile', async () => {
    const send = vi.fn(() => true)
    const user = userEvent.setup()
    render(<ProfileForm playerId="p1" displayName="Dana" send={send} serverError={null} />)

    await user.click(screen.getByRole('button', { name: 'Save my profile' }))

    expect(screen.getByRole('alert')).toHaveTextContent('City is required.')
    expect(send).not.toHaveBeenCalled()
  })

  test('greets the player by name', () => {
    render(<ProfileForm playerId="p1" displayName="Dana" send={vi.fn()} serverError={null} />)
    expect(screen.getByText('You’re in, Dana!')).toBeVisible()
  })
})

describe('buildProfileFields', () => {
  const required = { city: 'Haifa', favorite_food: 'pizza', hobby: 'chess', favorite_music: 'Rock' }

  test('rejects contact details and ID-like numbers', () => {
    const result = buildProfileFields({ ...required, personal_fact: 'mail dana@example.com' }, initialConsent())
    expect(result).toEqual({ error: PRIVACY_MESSAGE, fieldKey: 'personal_fact' })
  })

  test('rejects an out-of-range age', () => {
    expect(buildProfileFields({ ...required, age: '150' }, initialConsent())).toEqual({
      error: 'Age must be between 5 and 120.', fieldKey: 'age',
    })
  })

  test('rejects an unknown music style', () => {
    expect(buildProfileFields({ ...required, favorite_music: 'Polka' }, initialConsent())).toHaveProperty('error')
  })

  test('omits empty optional fields and collapses whitespace', () => {
    const result = buildProfileFields({ ...required, city: '  Tel   Aviv ' }, initialConsent())
    expect('fields' in result && result.fields.map((f) => f.field_key)).toEqual([
      'city',
      'favorite_food',
      'hobby',
      'favorite_music',
    ])
    expect('fields' in result && result.fields[0].value).toBe('Tel Aviv')
  })
})

 test('releases a pending profile after a disconnect without losing the draft', async () => {
  const props = { playerId: 'p1', displayName: 'Dana', send: vi.fn(() => true), serverError: null }
  const { rerender } = render(<ProfileForm {...props} connected />)
  const user = userEvent.setup()
  await fillRequired(user)
  await user.click(screen.getByRole('button', { name: 'Save my profile' }))
  expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled()
  rerender(<ProfileForm {...props} connected={false} />)
  rerender(<ProfileForm {...props} connected />)
  expect(screen.getByLabelText('City')).toHaveValue('Haifa')
  await user.click(screen.getByRole('button', { name: 'Save my profile' }))
  expect(props.send).toHaveBeenCalledTimes(2)
 })

vi.mock('../../legal/privacyInfo', () => ({ usePrivacyInfo: () => ({
  info: { policy_version: '2026-09-18', retention_days: 7, room_idle_ttl_minutes: 120,
    maintenance_interval_seconds: 300, raw_profiles_persisted: false },
  status: 'ready', retry: () => {},
}) }))
