import { HostRoomEntry } from '../features/host/HostRoomEntry'
import { PlayerRoomEntry } from '../features/player/PlayerRoomEntry'

export function App() {
  return (
    <main className="app-shell">
      <header className="welcome-copy">
        <p className="eyebrow">Who’s Who · Made for your group</p>
        <h1 id="app-title">MiZeMi</h1>
        <p>
          Turn the stories you share into a game everyone will remember.
        </p>
      </header>

      <div className="entry-grid" aria-labelledby="app-title">
        <PlayerRoomEntry />
        <HostRoomEntry />
      </div>

      <p className="privacy-note">No account needed. Just your group and a room code.</p>
    </main>
  )
}
