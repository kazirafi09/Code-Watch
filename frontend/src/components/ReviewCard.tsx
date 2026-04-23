import { api } from '../api/client'
import type { Review } from '../api/types'
import { formatTimestamp, basename } from '../lib/format'
import { severityBadge, severityBg } from '../lib/severity'
import { ReviewMarkdown } from './ReviewMarkdown'

interface Props {
  review: Review
  isStreaming: boolean
  isSelected: boolean
  onClick: () => void
  onDelete: (id: string) => void
}

export function ReviewCard({ review, isStreaming, isSelected, onClick, onDelete }: Props) {
  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(review.full_text)
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    onDelete(review.id)
  }

  const handleExport = async (e: React.MouseEvent) => {
    e.stopPropagation()
    const res = await api.exportReview(review.id)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `review_${basename(review.filename)}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const previewText = review.full_text.slice(0, 240)

  return (
    <article
      className={`group relative border rounded-xl p-4 cursor-pointer transition-all ${severityBg(review.severity)} ${
        isSelected
          ? 'ring-2 ring-accent-500/50 shadow-glow'
          : 'hover:border-white/20 hover:shadow-card'
      }`}
      onClick={onClick}
    >
      <header className="flex items-start justify-between gap-3 mb-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
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
          <h3 className="font-mono text-sm text-slate-100 truncate" title={review.filename}>
            {basename(review.filename)}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">{formatTimestamp(review.created_at)}</p>
        </div>
      </header>

      <ReviewMarkdown
        text={previewText}
        className="text-sm text-slate-300 leading-relaxed line-clamp-3"
      />

      {isStreaming && (
        <span className="inline-block w-1.5 h-3.5 bg-accent-400 animate-pulse ml-0.5 align-middle" />
      )}

      {!isStreaming && review.full_text && (
        <div
          className="flex items-center gap-1 mt-3 pt-3 border-t border-white/5 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          <button onClick={handleCopy} className="btn-ghost text-xs py-1" title="Copy text">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
            Copy
          </button>
          <button onClick={handleExport} className="btn-ghost text-xs py-1" title="Export as Markdown">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export
          </button>
          <button onClick={handleDelete} className="btn-ghost text-xs py-1 ml-auto text-rose-400 hover:text-rose-300" title="Delete">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
            </svg>
            Delete
          </button>
        </div>
      )}
    </article>
  )
}
