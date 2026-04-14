import { api } from '../api/client'
import type { Review } from '../api/types'
import { formatDuration, formatTimestamp, basename } from '../lib/format'
import { severityBadge } from '../lib/severity'

interface Props {
  review: Review
  isStreaming: boolean
  onDelete: (id: string) => void
  onClose: () => void
}

function highlightSeverity(text: string): string {
  return text
    .replace(/\b(critical|security|vulnerability|exploit|injection)\b/gi, '<span class="text-red-400 font-semibold">$1</span>')
    .replace(/\b(warning|bug|error|unsafe|deprecated)\b/gi, '<span class="text-amber-400">$1</span>')
    .replace(/\b(suggestion|recommend|consider|improve)\b/gi, '<span class="text-blue-400">$1</span>')
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
    <div className="flex flex-col h-full bg-gray-900 border-l border-gray-800">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between shrink-0">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-xs px-1.5 py-0.5 rounded font-semibold ${severityBadge(review.severity)}`}>
              {review.severity}
            </span>
            <span className="text-sm font-mono text-gray-200 truncate">{basename(review.filename)}</span>
          </div>
          <div className="text-xs text-gray-500 mt-0.5">{formatTimestamp(review.created_at)}</div>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-white ml-2 shrink-0">×</button>
      </div>

      {/* Meta */}
      <div className="px-4 py-2 border-b border-gray-800 flex gap-4 text-xs text-gray-500 shrink-0">
        <span>Lang: <span className="text-gray-400">{review.language || '—'}</span></span>
        <span>Mode: <span className="text-gray-400">{review.mode}</span></span>
        {review.duration_ms > 0 && (
          <span>Duration: <span className="text-gray-400">{formatDuration(review.duration_ms)}</span></span>
        )}
        <span className="truncate text-gray-600" title={review.filename}>{review.filename}</span>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4">
        <div
          className="text-sm font-mono text-gray-300 leading-relaxed whitespace-pre-wrap"
          dangerouslySetInnerHTML={{ __html: highlightSeverity(review.full_text) }}
        />
        {isStreaming && (
          <span className="inline-block w-2 h-4 bg-gray-400 animate-pulse ml-0.5 align-middle" />
        )}
      </div>

      {/* Actions */}
      {!isStreaming && (
        <div className="px-4 py-3 border-t border-gray-800 flex gap-3 shrink-0">
          <button
            onClick={handleCopy}
            className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded"
          >
            Copy
          </button>
          <button
            onClick={handleExport}
            className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded"
          >
            Export .md
          </button>
          <button
            onClick={() => onDelete(review.id)}
            className="text-xs bg-red-900 hover:bg-red-800 text-red-200 px-3 py-1.5 rounded ml-auto"
          >
            Delete
          </button>
        </div>
      )}
    </div>
  )
}
