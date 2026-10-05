import { useState, type ReactNode } from 'react'
import { LegalFooter } from '../legal/LegalFooter'
import { LegalPage, legalPageFromPath } from '../legal/LegalPage'
import { KnowledgeCredits } from './KnowledgeCredits'
import logo from '../assets/mizemi-logo.png'
import { I18nProvider, LanguageSelector, useI18n } from '../i18n/I18n'
import { SoundToggle } from '../audio/SoundToggle'

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
  const legalPage = legalPageFromPath(window.location.pathname)
  return <I18nProvider>{legalPage ? <AppShell><LegalPage page={legalPage} /></AppShell> : <AppContent />}</I18nProvider>
}

function AppShell({ children, inGame = false }: { children: ReactNode; inGame?: boolean }) {
  const { t } = useI18n()
  return <div className={`app-shell${inGame ? ' game-mode' : ''}`}>
    <a className="skip-link" href="#main-content">{t('Skip to main content')}</a>
    <header className="top-controls"><SoundToggle /><LanguageSelector /></header>
    <main id="main-content" tabIndex={-1}>{children}</main>
    <LegalFooter inGame={inGame} />
  </div>
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
      <AppShell inGame>
        <h1 className="sr-only">MiZeMi · {t('Host screen')}</h1>
        <HostGame session={session} onLeave={leave} />
        <KnowledgeCredits />
      </AppShell>
    )
  }
  if (session?.role === 'player') {
    return (
      <AppShell inGame>
        <h1 className="sr-only">MiZeMi · {t('Player screen')}</h1>
        <PlayerGame session={session} onLeave={leave} />
        <KnowledgeCredits />
      </AppShell>
    )
  }

  return (
    <AppShell>
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
    </AppShell>
  )
}
