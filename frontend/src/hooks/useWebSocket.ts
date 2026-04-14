import { useCallback, useEffect, useRef, useState } from 'react'
import type { WsEvent } from '../api/types'

const WS_URL = `ws://${window.location.host}/ws`
const MAX_BACKOFF = 30000

export function useWebSocket(onMessage: (event: WsEvent) => void) {
  const [isConnected, setIsConnected] = useState(false)
  const [connectionAttempts, setConnectionAttempts] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)
  const backoffRef = useRef(1000)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      setConnectionAttempts(0)
      backoffRef.current = 1000
    }

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as WsEvent
        onMessageRef.current(data)
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      wsRef.current = null
      const delay = backoffRef.current
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF)
      setConnectionAttempts((n) => n + 1)
      setTimeout(connect, delay)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  return { isConnected, connectionAttempts }
}
