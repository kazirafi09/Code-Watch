import { api } from '../api/client'
import type { Review } from '../api/types'
import { formatDuration, formatTimestamp, basename } from '../lib/format'
import { severityBadge } from '../lib/severity'
import { ReviewMarkdown } from './ReviewMarkdown'

interface Props {
  review: Review
  isStreaming: boolean
  onDelete: (id: string) => void
  onClose: () => void
}

function modeLabel(mode: string): string {
  if (mode === 'full+diff') return 'full + diff'
  if (mode === 'diff') return 'diff only'
  return 'full file'
}

function modeTooltip(mode: string): string {
  if (mode === 'full+diff') return 'Full file plus recent diff — model has architectural context and what changed.'
  if (mode === 'diff') return 'Diff-only review — model only sees changed lines. Coverage may be degraded on architectural issues.'
  return 'Full file review — model sees the whole file.'
}

export function ReviewDetail({ review, isStreaming, onDelete, onClose }: Props) {
  const handleCopy = () => navigator.clipboard.writeText(review.full_text)

  const handleExport = async () => {
    const res = await api.exportReview(review.id)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `review_${basename(review.filename)}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-full bg-surface-1 md:border-l border-white/5 shadow-2xl md:shadow-none">
      {/* Header */}
      <div className="px-5 py-4 border-b border-white/5 flex items-start justify-between gap-3 shrink-0">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className={`chip ${severityBadge(review.severity)} capitalize`}>
              {review.severity}
            </span>
            {isStreaming && (
              <span className="chip bg-accent-500/15 text-accent-300 border border-accent-500/30">
                <span className="w-1.5 h-1.5 rounded-full bg-accent-400 animate-pulse" />
                Streaming
              </span>
            )}
          </div>
          <h2 className="text-sm font-mono text-slate-100 truncate" title={review.filename}>
            {basename(review.filename)}
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">{formatTimestamp(review.created_at)}</p>
        </div>
        <button onClick={onClose} className="btn-ghost p-1.5" aria-label="Close">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* Meta */}
      <div className="px-5 py-3 border-b border-white/5 grid grid-cols-2 gap-2 text-xs shrink-0 bg-surface-2/30">
        <div className="flex flex-col">
          <span className="text-slate-500 text-[10px] uppercase tracking-wider">Language</span>
          <span className="text-slate-200 mt-0.5">{review.language || '—'}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-slate-500 text-[10px] uppercase tracking-wider">Mode</span>
          <span className="text-slate-200 mt-0.5" title={modeTooltip(review.mode)}>{modeLabel(review.mode)}</span>
        </div>
        {review.duration_ms > 0 && (
          <div className="flex flex-col">
            <span className="text-slate-500 text-[10px] uppercase tracking-wider">Duration</span>
            <span className="text-slate-200 mt-0.5">{formatDuration(review.duration_ms)}</span>
          </div>
        )}
        <div className="flex flex-col col-span-2 min-w-0">
          <span className="text-slate-500 text-[10px] uppercase tracking-wider">Path</span>
          <span className="text-slate-400 mt-0.5 truncate font-mono text-[11px]" title={review.filename}>
            {review.filename}
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        <ReviewMarkdown
          text={review.full_text}
          className="text-sm text-slate-200 leading-relaxed"
        />
        {isStreaming && (
          <span className="inline-block w-2 h-4 bg-accent-400 animate-pulse ml-0.5 align-middle" />
        )}
      </div>

      {/* Actions */}
      {!isStreaming && (
        <div className="px-5 py-3 border-t border-white/5 flex gap-2 shrink-0 bg-surface-2/30">
          <button onClick={handleCopy} className="btn-secondary">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
            Copy
          </button>
          <button onClick={handleExport} className="btn-secondary">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export .md
          </button>
          <button onClick={() => onDelete(review.id)} className="btn-danger ml-auto">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
            </svg>
            Delete
          </button>
        </div>
      )}
    </div>
  )
}
