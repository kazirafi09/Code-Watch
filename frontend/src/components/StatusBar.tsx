import type { StatusResponse } from '../api/types'
import { formatDuration } from '../lib/format'

interface Props {
  status: StatusResponse
}

export function StatusBar({ status }: Props) {
  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-gray-900 border-t border-gray-800 text-xs text-gray-400 shrink-0">
      {/* Ollama status */}
      <div className="flex items-center gap-1.5">
        <span
          className={`w-2 h-2 rounded-full ${status.ollama_ok ? 'bg-green-500' : 'bg-red-500'}`}
        />
        <span>{status.ollama_ok ? 'Ollama connected' : 'Ollama offline'}</span>
      </div>

      {status.model && (
        <span className="text-gray-500">
          Model: <span className="text-gray-300">{status.model}</span>
        </span>
      )}

      {status.queue_depth > 0 && (
        <span className="text-amber-400">Queue: {status.queue_depth}</span>
      )}

      {status.last_duration_ms != null && (
        <span>Last: {formatDuration(status.last_duration_ms)}</span>
      )}

      {status.tokens_per_sec != null && (
        <span>{status.tokens_per_sec.toFixed(1)} tok/s</span>
      )}

      <span className="ml-auto text-gray-600">CodeWatch</span>
    </div>
  )
}
