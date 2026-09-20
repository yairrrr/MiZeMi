import { act, renderHook, waitFor, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { isPrivacyInfo, usePrivacyInfo, POLICY_VERSION } from './privacyInfo'
import { ProfileForm } from '../features/player/ProfileForm'

const facts = { policy_version: POLICY_VERSION, raw_profiles_persisted: false,
  retention_days: 7, room_idle_ttl_minutes: 120, maintenance_interval_seconds: 300 }
afterEach(() => vi.unstubAllGlobals())

test.each([null, {}, { ...facts, raw_profiles_persisted: true }, { ...facts, policy_version: 'old' },
  { ...facts, retention_days: 0 }, { ...facts, retention_days: '7' }])('rejects incompatible policy facts: %j', value => {
  expect(isPrivacyInfo(value)).toBe(false)
})

test('loads actual retention without credentials or caching', async () => {
  const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...facts, retention_days: 3 }) })
  vi.stubGlobal('fetch', fetcher)
  const { result } = renderHook(usePrivacyInfo)
  await waitFor(() => expect(result.current.status).toBe('ready'))
  expect(result.current.info?.retention_days).toBe(3)
  expect(fetcher).toHaveBeenCalledWith(expect.stringContaining('/api/v1/privacy-info'),
    expect.objectContaining({ credentials: 'omit', cache: 'no-store', signal: expect.any(AbortSignal) }))
})

test('profile submission fails closed on an older backend and retry recovers', async () => {
  const fetcher = vi.fn().mockResolvedValueOnce({ ok: false, json: async () => ({ detail: 'Not Found' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => facts })
  vi.stubGlobal('fetch', fetcher)
  const send = vi.fn()
  render(<ProfileForm playerId="synthetic" displayName="Synthetic" send={send} serverError={null} />)
  const submit = screen.getByRole('button', { name: 'Save my profile' })
  expect(submit).toBeDisabled()
  await screen.findByText('Current retention settings are unavailable. Please retry before submitting personal information.')
  expect(submit).toBeDisabled()
  expect(send).not.toHaveBeenCalled()
  await act(async () => screen.getByRole('button', { name: 'Try again' }).click())
  await waitFor(() => expect(submit).toBeEnabled())
  expect(screen.getByText(/after 7 days from their last save/)).toBeVisible()
  expect(screen.getByText(/A disabled field does not influence question generation/)).toBeVisible()
})
