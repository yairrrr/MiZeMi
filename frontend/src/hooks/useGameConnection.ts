import { useCallback, useEffect, useReducer, useRef, useState } from 'react'

import { getWebSocketBaseUrl } from '../config'
import { GameSocket, type SocketFactory, type SocketStatus } from '../realtime/gameSocket'
import {
  buildHostWebSocketUrl,
  HOST_PROTOCOL,
  PLAYER_PROTOCOL,
} from '../realtime/hostWebSocketUrl'
import { buildPlayerWebSocketUrl } from '../realtime/playerWebSocketUrl'
import { gameReducer, initialGameView, type GameView } from '../state/gameReducer'
import type { Session } from '../state/session'
import type { ClientToServerEvent } from '../types'

export type SendFn = (event: ClientToServerEvent, payload?: Record<string, unknown>) => boolean

export type GameConnection = {
  view: GameView
  status: SocketStatus
  send: SendFn
  dismissError: () => void
}

/** Connects this tab's session to its room and folds server events into state. */
export function useGameConnection(session: Session, createSocket?: SocketFactory): GameConnection {
  const [view, dispatch] = useReducer(gameReducer, initialGameView)
  const [status, setStatus] = useState<SocketStatus>('connecting')
  const socketRef = useRef<GameSocket | null>(null)
  const pendingCommand = useRef<ClientToServerEvent | null>(null)

  useEffect(() => {
    const base = getWebSocketBaseUrl()
    const isHost = session.role === 'host'
    const socket = new GameSocket({
      url: isHost
        ? buildHostWebSocketUrl(base, session.room_code)
        : buildPlayerWebSocketUrl(base, session.room_code, session.player_id),
      protocols: isHost
        ? [HOST_PROTOCOL, session.host_token]
        : [PLAYER_PROTOCOL, session.player_token],
      gameId: session.game_id,
      onMessage: (message, receivedAt) => {
        if (message.event === 'room.updated' || message.event === 'error' || message.event === 'answer.accepted') {
          pendingCommand.current = null
        }
        dispatch({ type: 'message', message, receivedAt })
      },
      onStatus: (next) => {
        if (next !== 'open') pendingCommand.current = null
        setStatus(next)
      },
      createSocket,
    })
    socketRef.current = socket
    socket.connect()
    return () => {
      socket.close()
      if (socketRef.current === socket) {
        socketRef.current = null
      }
    }
  }, [session, createSocket])

  const send = useCallback<SendFn>(
    (event, payload) => {
      if (pendingCommand.current === event) return false
      const sent = socketRef.current?.send(event, payload) ?? false
      if (sent) pendingCommand.current = event
      return sent
    },
    [],
  )
  const dismissError = useCallback(() => dispatch({ type: 'dismissError' }), [])

  return { view, status, send, dismissError }
}
