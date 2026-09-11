import { useState } from 'react'
import { KnowledgeCredits } from './KnowledgeCredits'
import logo from '../assets/mizemi-logo.png'
import { I18nProvider, LanguageSelector, useI18n } from '../i18n/I18n'

import { HostGame } from '../features/host/HostGame'
import { HostRoomEntry } from '../features/host/HostRoomEntry'
import { PlayerGame } from '../features/player/PlayerGame'
import { PlayerRoomEntry } from '../features/player/PlayerRoomEntry'
import { clearSession, loadSession, saveSession, type Session } from '../state/session'

function roomCodeFromUrl(): string {
  try {
    return new URLSearchParams(window.location.search).get('room')?.slice(0, 12) ?? ''
  } catch {
    return ''
  }
}

export function App() {
  return <I18nProvider><AppContent /></I18nProvider>
}

function AppContent() {
  const { t } = useI18n()
  const [session, setSession] = useState<Session | null>(() => loadSession())

  function begin(next: Session) {
    saveSession(next)
    setSession(next)
  }

  function leave() {
    clearSession()
    setSession(null)
  }

  if (session?.role === 'host') {
    return (
      <main className="app-shell game-mode">
        <LanguageSelector />
        <HostGame session={session} onLeave={leave} />
        <KnowledgeCredits />
      </main>
    )
  }
  if (session?.role === 'player') {
    return (
      <main className="app-shell game-mode">
        <LanguageSelector />
        <PlayerGame session={session} onLeave={leave} />
        <KnowledgeCredits />
      </main>
    )
  }

  return (
    <main className="app-shell">
      <LanguageSelector />
      <header className="welcome-copy">

        <h1 id="app-title" className="brand-heading"><img className="brand-logo" src={logo} width={1254} height={1254} alt="MiZeMi" /></h1>
        <p>{t('Turn the stories you share into a game everyone will remember.')}</p>
      </header>

      <div className="entry-grid" aria-labelledby="app-title">
        <PlayerRoomEntry
          initialRoomCode={roomCodeFromUrl()}
          onJoined={(roomCode, response) =>
            begin({
              role: 'player',
              room_code: roomCode,
              game_id: response.game_id,
              player_id: response.player.player_id,
              player_token: response.player_token,
              display_name: response.player.display_name,
            })
          }
        />
        <HostRoomEntry
          onCreated={(room) =>
            begin({
              role: 'host',
              room_code: room.room_code,
              game_id: room.game_id,
              host_token: room.host_token,
            })
          }
        />
      </div>

      <p className="privacy-note">{t('No account needed. Just your group and a room code.')}</p>
      <KnowledgeCredits />
    </main>
  )
}
