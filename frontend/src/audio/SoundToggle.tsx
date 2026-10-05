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
      <SpeakerIcon muted={muted} />
    </button>
  )
}

/** Brand two-tone speaker: purple body with yellow waves; grey with an X when muted. */
function SpeakerIcon({ muted }: { muted: boolean }) {
  const body = muted ? '#b9b3c9' : '#6547cb'
  return (
    <svg className="sound-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d="M11 5 6 9H3.5a1 1 0 0 0-1 1v4a1 1 0 0 0 1 1H6l5 4z" fill={body} stroke={body} strokeWidth="1.6" />
      {muted ? (
        <path d="m16 9 5 6M21 9l-5 6" stroke="#8f88a3" strokeWidth="2.2" />
      ) : (
        <>
          <path d="M15.5 8.5a5 5 0 0 1 0 7" stroke="#f2b43a" strokeWidth="2.2" />
          <path d="M18.5 5.5a9 9 0 0 1 0 13" stroke="#f2b43a" strokeWidth="2.2" />
        </>
      )}
    </svg>
  )
}
