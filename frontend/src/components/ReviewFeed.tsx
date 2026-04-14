import { useState } from 'react'
import type { Review } from '../api/types'
import { ReviewCard } from './ReviewCard'

interface Props {
  reviews: Review[]
  streamingIds: Set<string>
  selectedId: string | null
  onSelect: (review: Review) => void
  onDelete: (id: string) => void
  onLoadMore: () => void
  total: number
  loading: boolean
  onFilterChange: (filters: { severity: string; search: string }) => void
}

const SEVERITIES = ['', 'critical', 'warning', 'suggestion']

export function ReviewFeed({
  reviews,
  streamingIds,
  selectedId,
  onSelect,
  onDelete,
  onLoadMore,
  total,
  loading,
  onFilterChange,
}: Props) {
  const [severity, setSeverity] = useState('')
  const [search, setSearch] = useState('')

  const handleSeverity = (s: string) => {
    setSeverity(s)
    onFilterChange({ severity: s, search })
  }

  const handleSearch = (s: string) => {
    setSearch(s)
    onFilterChange({ severity, search: s })
  }

  return (
    <div className="flex flex-col h-full">
      {/* Filter bar */}
      <div className="px-3 py-2 border-b border-gray-800 flex items-center gap-2 shrink-0 flex-wrap">
        <div className="flex gap-1">
          {SEVERITIES.map((s) => (
            <button
              key={s || 'all'}
              onClick={() => handleSeverity(s)}
              className={`text-xs px-2 py-1 rounded transition-colors ${
                severity === s
                  ? 'bg-gray-600 text-white'
                  : 'text-gray-500 hover:bg-gray-800 hover:text-gray-200'
              }`}
            >
              {s || 'All'}
            </button>
          ))}
        </div>
        <input
          type="search"
          placeholder="Search..."
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="ml-auto bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 w-40"
        />
      </div>

      {/* Feed */}
      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-2">
        {reviews.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-600 py-16">
            <div className="text-4xl mb-4">👁</div>
            <div className="text-sm mb-1">No reviews yet</div>
            <div className="text-xs">
              Add a project in the sidebar, then edit a file to trigger a review.
            </div>
          </div>
        )}

        {reviews.map((review) => (
          <ReviewCard
            key={review.id}
            review={review}
            isStreaming={streamingIds.has(review.id)}
            isSelected={review.id === selectedId}
            onClick={() => onSelect(review)}
            onDelete={onDelete}
          />
        ))}

        {reviews.length < total && (
          <button
            onClick={onLoadMore}
            className="text-xs text-gray-500 hover:text-gray-300 py-2 text-center"
          >
            Load more ({total - reviews.length} remaining)
          </button>
        )}

        {loading && (
          <div className="text-xs text-gray-600 text-center py-4">Loading...</div>
        )}
      </div>
    </div>
  )
}
