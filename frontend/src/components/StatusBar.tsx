import { api } from '../api/client'
import type { StatusResponse } from '../api/types'
import { formatDuration } from '../lib/format'

interface Props {
  status: StatusResponse
}

export function StatusBar({ status }: Props) {
  const hasQueue = status.queue_depth > 0 || status.pending_reviews > 0

  return (
    <div className="flex items-center gap-2 sm:gap-4 px-4 sm:px-6 h-9 bg-surface-1/80 backdrop-blur-md border-t border-white/5 text-xs text-slate-400 shrink-0 overflow-x-auto scrollbar-none">
      {/* Ollama status */}
      <div className="flex items-center gap-1.5 shrink-0">
        <span className={`w-2 h-2 rounded-full ${status.ollama_ok ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-rose-400'}`} />
        <span className="whitespace-nowrap">{status.ollama_ok ? 'Ollama connected' : 'Ollama offline'}</span>
      </div>

      {status.model && (
        <span className="text-slate-500 shrink-0 whitespace-nowrap">
          <span className="text-slate-600">Model</span> <span className="text-slate-300 font-mono">{status.model}</span>
        </span>
      )}

      {hasQueue && (
        <button
          className="chip bg-amber-500/15 text-amber-300 border border-amber-500/30 hover:bg-amber-500/25 transition-colors shrink-0 cursor-pointer"
          title="Click to clear queue and orphaned pending reviews"
          onClick={() => api.clearQueue()}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
          {status.queue_depth > 0 ? `Queue: ${status.queue_depth}` : `Pending: ${status.pending_reviews}`}
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}

      {status.last_duration_ms != null && (
        <span className="shrink-0 whitespace-nowrap">
          <span className="text-slate-600">Last</span> <span className="text-slate-300">{formatDuration(status.last_duration_ms)}</span>
        </span>
      )}

      {status.tokens_per_sec != null && (
        <span className="shrink-0 whitespace-nowrap">
          <span className="text-slate-300">{status.tokens_per_sec.toFixed(1)}</span> <span className="text-slate-600">tok/s</span>
        </span>
      )}

      <span className="ml-auto text-slate-600 shrink-0 hidden sm:block">CodeWatch</span>
    </div>
  )
}
