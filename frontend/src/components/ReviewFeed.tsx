import { useState } from 'react'
import type { Review } from '../api/types'
import { ReviewCard } from './ReviewCard'
import { severityDot } from '../lib/severity'

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

const SEVERITIES = [
  { value: '', label: 'All' },
  { value: 'critical', label: 'Critical' },
  { value: 'warning', label: 'Warning' },
  { value: 'suggestion', label: 'Suggestion' },
]

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
      <div className="px-4 sm:px-6 py-3 border-b border-white/5 bg-surface-1/50 backdrop-blur-sm flex flex-col sm:flex-row sm:items-center gap-3 shrink-0">
        <div className="flex gap-1 overflow-x-auto -mx-1 px-1 sm:overflow-visible scrollbar-none">
          {SEVERITIES.map((s) => (
            <button
              key={s.value || 'all'}
              onClick={() => handleSeverity(s.value)}
              className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full transition-colors shrink-0 border ${
                severity === s.value
                  ? 'bg-white/10 text-slate-100 border-white/15'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border-transparent'
              }`}
            >
              {s.value && <span className={`w-1.5 h-1.5 rounded-full ${severityDot(s.value)}`} />}
              {s.label}
            </button>
          ))}
        </div>
        <div className="sm:ml-auto relative w-full sm:w-64">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="search"
            placeholder="Search reviews..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="input pl-9 py-1.5 text-xs"
          />
        </div>
      </div>

      {/* Feed */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
        {reviews.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center py-20">
            <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-500/20 to-violet-500/10 border border-accent-500/20 flex items-center justify-center mb-4">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-accent-400">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            </div>
            <h3 className="text-base font-medium text-slate-200 mb-1">No reviews yet</h3>
            <p className="text-sm text-slate-500 max-w-sm">
              Add a project in the sidebar, then save a file to trigger your first AI code review.
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-3 max-w-[1600px] mx-auto">
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
        </div>

        {reviews.length < total && (
          <div className="flex justify-center pt-4">
            <button onClick={onLoadMore} className="btn-secondary">
              Load more ({total - reviews.length} remaining)
            </button>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center gap-2 text-xs text-slate-500 py-6">
            <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="2" x2="12" y2="6" />
              <line x1="12" y1="18" x2="12" y2="22" />
              <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
              <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
              <line x1="2" y1="12" x2="6" y2="12" />
              <line x1="18" y1="12" x2="22" y2="12" />
              <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
              <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
            </svg>
            Loading reviews
          </div>
        )}
      </div>
    </div>
  )
}
