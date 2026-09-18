import { useEffect, useState } from 'react'
import { getApiBaseUrl } from '../config'

export const POLICY_VERSION = '2026-09-18'
export type PrivacyInfo = {
  policy_version: string
  retention_days: number
  room_idle_ttl_minutes: number
  maintenance_interval_seconds: number
  raw_profiles_persisted: false
}

export function isPrivacyInfo(value: unknown): value is PrivacyInfo {
  if (!value || typeof value !== 'object') return false
  const info = value as Record<string, unknown>
  return info.policy_version === POLICY_VERSION && info.raw_profiles_persisted === false &&
    ['retention_days', 'room_idle_ttl_minutes', 'maintenance_interval_seconds'].every(
      key => typeof info[key] === 'number' && Number.isSafeInteger(info[key]) && Number(info[key]) > 0,
    )
}

/** Fetch public policy facts only; never send session credentials or profiles. */
export function usePrivacyInfo() {
  const [info, setInfo] = useState<PrivacyInfo | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'unavailable'>('loading')
  const [attempt, retry] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let active = true
    const timeout = window.setTimeout(() => controller.abort(), 15_000)
    setStatus('loading')
    async function load() {
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/v1/privacy-info`, {
          signal: controller.signal, credentials: 'omit', cache: 'no-store',
        })
        const data: unknown = await response.json()
        if (!response.ok || !isPrivacyInfo(data)) throw new Error('Policy facts unavailable')
        if (active) { setInfo(data); setStatus('ready') }
      } catch {
        if (active) { setInfo(null); setStatus('unavailable') }
      } finally { window.clearTimeout(timeout) }
    }
    void load()
    return () => { active = false; controller.abort(); window.clearTimeout(timeout) }
  }, [attempt])
  return { info, status, retry: () => retry(value => value + 1) }
}
