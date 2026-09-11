/** ``/ws/rooms/{room_code}/host`` — the host token travels as a subprotocol. */
export function buildHostWebSocketUrl(webSocketBaseUrl: string, roomCode: string): string {
  const url = new URL(webSocketBaseUrl)

  url.pathname = `/ws/rooms/${encodeURIComponent(roomCode)}/host`
  url.search = ''
  url.hash = ''

  return url.toString()
}

export const HOST_PROTOCOL = 'mizemi.host'
export const PLAYER_PROTOCOL = 'mizemi.player'
