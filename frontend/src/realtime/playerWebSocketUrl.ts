export function buildPlayerWebSocketUrl(
  webSocketBaseUrl: string,
  roomCode: string,
  playerId: string,
): string {
  const url = new URL(webSocketBaseUrl)

  url.pathname = `/ws/rooms/${encodeURIComponent(roomCode)}`
  url.search = new URLSearchParams({ player_id: playerId }).toString()
  url.hash = ''

  return url.toString()
}
