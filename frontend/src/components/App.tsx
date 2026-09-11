import { useState } from 'react'

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
        <HostGame session={session} onLeave={leave} />
      </main>
    )
  }
  if (session?.role === 'player') {
    return (
      <main className="app-shell game-mode">
        <PlayerGame session={session} onLeave={leave} />
      </main>
    )
  }

  return (
    <main className="app-shell">
      <header className="welcome-copy">
        <p className="eyebrow">Who’s Who · Made for your group</p>
        <h1 id="app-title">MiZeMi</h1>
        <p>Turn the stories you share into a game everyone will remember.</p>
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

      <p className="privacy-note">No account needed. Just your group and a room code.</p>
    </main>
  )
}
