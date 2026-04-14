import { useCallback, useState } from 'react'
import type { Review, WsEvent } from './api/types'
import { ReviewDetail } from './components/ReviewDetail'
import { ReviewFeed } from './components/ReviewFeed'
import { Settings } from './components/Settings'
import { Sidebar } from './components/Sidebar'
import { StatusBar } from './components/StatusBar'
import { ToastContainer, type ToastMessage } from './components/Toast'
import { useProjects } from './hooks/useProjects'
import { useReviews } from './hooks/useReviews'
import { useStatus } from './hooks/useStatus'
import { useWebSocket } from './hooks/useWebSocket'

let toastCounter = 0

export default function App() {
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [selectedReview, setSelectedReview] = useState<Review | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [toasts, setToasts] = useState<ToastMessage[]>([])
  const [filters, setFilters] = useState({ severity: '', search: '' })

  const { projects, addProject, removeProject } = useProjects()
  const { status, update: updateStatus } = useStatus()

  const reviewFilters = {
    project_id: selectedProjectId ?? undefined,
    severity: filters.severity || undefined,
    search: filters.search || undefined,
  }

  const {
    reviews,
    total,
    loading,
    streamingIds,
    fetchMore,
    handleReviewStart,
    handleReviewToken,
    handleReviewDone,
    deleteReview,
  } = useReviews(reviewFilters)

  const addToast = useCallback((level: ToastMessage['level'], message: string) => {
    const id = String(++toastCounter)
    setToasts((prev) => [...prev, { id, level, message }])
  }, [])

  const handleWsMessage = useCallback((event: WsEvent) => {
    switch (event.type) {
      case 'review_start':
        handleReviewStart(event)
        break
      case 'review_token':
        handleReviewToken(event)
        if (selectedReview?.id === event.review_id) {
          setSelectedReview((prev) =>
            prev ? { ...prev, full_text: (prev.full_text ?? '') + event.token } : prev
          )
        }
        break
      case 'review_done':
        handleReviewDone(event)
        if (selectedReview?.id === event.review_id) {
          setSelectedReview((prev) =>
            prev ? { ...prev, full_text: event.full_text, severity: event.severity as Review['severity'] } : prev
          )
        }
        break
      case 'queue_update':
        updateStatus({ queue_depth: event.depth })
        break
      case 'status_update':
        updateStatus(event)
        break
      case 'toast':
        addToast(event.level, event.message)
        break
    }
  }, [handleReviewStart, handleReviewToken, handleReviewDone, updateStatus, addToast, selectedReview])

  const { isConnected } = useWebSocket(handleWsMessage)

  const handleDeleteReview = useCallback(async (id: string) => {
    await deleteReview(id)
    if (selectedReview?.id === id) setSelectedReview(null)
  }, [deleteReview, selectedReview])

  const handleSelectProject = (id: number | null) => {
    setSelectedProjectId(id)
    setSelectedReview(null)
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold text-white tracking-tight">CodeWatch</span>
          <span
            className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}
            title={isConnected ? 'Connected' : 'Disconnected'}
          />
        </div>
        <button
          onClick={() => setShowSettings(true)}
          className="text-xs text-gray-500 hover:text-gray-300 px-2 py-1 rounded hover:bg-gray-800"
        >
          Settings
        </button>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          projects={projects}
          selectedProjectId={selectedProjectId}
          onSelect={handleSelectProject}
          onAdd={async (name, path) => {
            await addProject(name, path)
          }}
          onRemove={async (id) => {
            await removeProject(id)
            if (selectedProjectId === id) setSelectedProjectId(null)
          }}
        />

        {/* Feed */}
        <main className="flex-1 overflow-hidden">
          <ReviewFeed
            reviews={reviews}
            streamingIds={streamingIds}
            selectedId={selectedReview?.id ?? null}
            onSelect={setSelectedReview}
            onDelete={handleDeleteReview}
            onLoadMore={fetchMore}
            total={total}
            loading={loading}
            onFilterChange={setFilters}
          />
        </main>

        {/* Detail panel */}
        {selectedReview && (
          <div className="w-96 shrink-0 overflow-hidden">
            <ReviewDetail
              review={selectedReview}
              isStreaming={streamingIds.has(selectedReview.id)}
              onDelete={handleDeleteReview}
              onClose={() => setSelectedReview(null)}
            />
          </div>
        )}
      </div>

      <StatusBar status={status} />

      {showSettings && <Settings onClose={() => setShowSettings(false)} />}

      <ToastContainer toasts={toasts} onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))} />
    </div>
  )
}
