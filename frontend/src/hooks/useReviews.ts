import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Review } from '../api/types'

interface Filters {
  project_id?: number
  severity?: string
  search?: string
}

const PAGE_SIZE = 50

export function useReviews(filters: Filters) {
  const [reviews, setReviews] = useState<Review[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  // Track streaming text keyed by review_id
  const streamingRef = useRef<Map<string, string>>(new Map())
  const [streamingIds, setStreamingIds] = useState<Set<string>>(new Set())

  const fetchReviews = useCallback(async (offset = 0) => {
    setLoading(true)
    try {
      const data = await api.getReviews({ ...filters, limit: PAGE_SIZE, offset })
      setReviews(offset === 0 ? data.items : (prev) => [...prev, ...data.items])
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }, [filters.project_id, filters.severity, filters.search])  // eslint-disable-line

  useEffect(() => {
    fetchReviews(0)
  }, [fetchReviews])

  const handleReviewStart = useCallback((event: { review_id: string; project_id: number; filename: string; timestamp: string }) => {
    streamingRef.current.set(event.review_id, '')
    setStreamingIds((prev) => new Set([...prev, event.review_id]))
    const newReview: Review = {
      id: event.review_id,
      project_id: event.project_id,
      filename: event.filename,
      language: '',
      full_text: '',
      severity: 'pending',
      mode: 'full',
      prompt_tokens: 0,
      completion_tokens: 0,
      duration_ms: 0,
      created_at: event.timestamp,
    }
    setReviews((prev) => [newReview, ...prev])
  }, [])

  const handleReviewToken = useCallback((event: { review_id: string; token: string }) => {
    const current = streamingRef.current.get(event.review_id) ?? ''
    const updated = current + event.token
    streamingRef.current.set(event.review_id, updated)
    setReviews((prev) =>
      prev.map((r) => r.id === event.review_id ? { ...r, full_text: updated } : r)
    )
  }, [])

  const handleReviewDone = useCallback((event: { review_id: string; full_text: string; severity: string }) => {
    streamingRef.current.delete(event.review_id)
    setStreamingIds((prev) => {
      const next = new Set(prev)
      next.delete(event.review_id)
      return next
    })
    setReviews((prev) =>
      prev.map((r) =>
        r.id === event.review_id
          ? { ...r, full_text: event.full_text, severity: event.severity as Review['severity'] }
          : r
      )
    )
  }, [])

  const deleteReview = useCallback(async (id: string) => {
    await api.deleteReview(id)
    setReviews((prev) => prev.filter((r) => r.id !== id))
    setTotal((n) => n - 1)
  }, [])

  return {
    reviews,
    total,
    loading,
    streamingIds,
    fetchMore: () => fetchReviews(reviews.length),
    handleReviewStart,
    handleReviewToken,
    handleReviewDone,
    deleteReview,
    refresh: () => fetchReviews(0),
  }
}
