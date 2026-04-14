import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { StatusResponse } from '../api/types'

export function useStatus() {
  const [status, setStatus] = useState<StatusResponse>({
    ollama_ok: false,
    model: '',
    queue_depth: 0,
    last_duration_ms: null,
    tokens_per_sec: null,
  })

  useEffect(() => {
    const poll = async () => {
      try {
        const s = await api.getStatus()
        setStatus(s)
      } catch {
        setStatus((prev) => ({ ...prev, ollama_ok: false }))
      }
    }

    poll()
    const id = setInterval(poll, 10000)
    return () => clearInterval(id)
  }, [])

  const update = (partial: Partial<StatusResponse>) => {
    setStatus((prev) => ({ ...prev, ...partial }))
  }

  return { status, update }
}
