import { useSyncExternalStore } from 'react'

import { useI18n } from '../i18n/I18n'
import { isMuted, setMuted, subscribeMuted, unlockAudio } from './sound'

export function useMuted(): boolean {
  return useSyncExternalStore(subscribeMuted, isMuted, isMuted)
}

/** Header switch that mutes every game sound; remembered on this device. */
export function SoundToggle() {
  const { t } = useI18n()
  const muted = useMuted()
  return (
    <button
      type="button"
      className="sound-toggle"
      aria-pressed={!muted}
      aria-label={t(muted ? 'Sound off — turn sound on' : 'Sound on — turn sound off')}
      title={t(muted ? 'Sound off — turn sound on' : 'Sound on — turn sound off')}
      onClick={() => {
        setMuted(!muted)
        if (muted) unlockAudio()
      }}
    >
      <span aria-hidden="true">{muted ? '🔇' : '🔊'}</span>
    </button>
  )
}
