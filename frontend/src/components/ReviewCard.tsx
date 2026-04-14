import { api } from '../api/client'
import type { Review } from '../api/types'
import { formatTimestamp, basename } from '../lib/format'
import { severityBadge, severityBg } from '../lib/severity'

interface Props {
  review: Review
  isStreaming: boolean
  isSelected: boolean
  onClick: () => void
  onDelete: (id: string) => void
}

function highlightSeverity(text: string): string {
  return text
    .replace(/\b(critical|security|vulnerability|exploit|injection)\b/gi, '<span class="text-red-400 font-semibold">$1</span>')
    .replace(/\b(warning|bug|error|unsafe|deprecated)\b/gi, '<span class="text-amber-400">$1</span>')
    .replace(/\b(suggestion|recommend|consider|improve)\b/gi, '<span class="text-blue-400">$1</span>')
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

  const previewText = review.full_text.slice(0, 200)

  return (
    <div
      className={`border rounded p-3 cursor-pointer transition-colors ${severityBg(review.severity)} ${
        isSelected ? 'ring-1 ring-blue-500' : 'hover:brightness-110'
      }`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-xs text-gray-300 truncate font-mono">{basename(review.filename)}</span>
        <span className={`text-xs px-1.5 py-0.5 rounded font-semibold shrink-0 ${severityBadge(review.severity)}`}>
          {review.severity}
        </span>
      </div>

      <div className="text-xs text-gray-500 mb-2">{formatTimestamp(review.created_at)}</div>

      <div
        className="text-xs text-gray-300 leading-relaxed line-clamp-3 font-mono"
        dangerouslySetInnerHTML={{ __html: highlightSeverity(previewText) }}
      />

      {isStreaming && (
        <span className="inline-block w-1.5 h-3 bg-gray-400 animate-pulse ml-0.5" />
      )}

      {!isStreaming && review.full_text && (
        <div className="flex gap-2 mt-2" onClick={(e) => e.stopPropagation()}>
          <button onClick={handleCopy} className="text-xs text-gray-500 hover:text-gray-200">Copy</button>
          <button onClick={handleExport} className="text-xs text-gray-500 hover:text-gray-200">Export</button>
          <button onClick={handleDelete} className="text-xs text-red-600 hover:text-red-400">Delete</button>
        </div>
      )}
    </div>
  )
}
