import { useCallback, useEffect, useState } from 'react'
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
  const [showSidebar, setShowSidebar] = useState(false)
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
    setShowSidebar(false)
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (selectedReview) setSelectedReview(null)
        else if (showSidebar) setShowSidebar(false)
        else if (showSettings) setShowSettings(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selectedReview, showSidebar, showSettings])

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 sm:px-6 h-14 bg-surface-1/80 backdrop-blur-md border-b border-white/5 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowSidebar(true)}
            className="lg:hidden btn-ghost p-1.5"
            aria-label="Open projects"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-500 to-violet-600 flex items-center justify-center shadow-glow">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            </div>
            <div className="flex flex-col leading-tight">
              <span className="text-sm font-semibold text-slate-100 tracking-tight">CodeWatch</span>
              <span className="hidden sm:block text-[10px] text-slate-500">Local AI code review</span>
            </div>
          </div>
          <span
            className={`ml-2 chip ${isConnected ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-300 border border-rose-500/30'}`}
            title={isConnected ? 'Connected' : 'Disconnected'}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
            <span className="hidden sm:inline">{isConnected ? 'Live' : 'Offline'}</span>
          </span>
        </div>
        <button
          onClick={() => setShowSettings(true)}
          className="btn-ghost"
          aria-label="Settings"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          <span className="hidden sm:inline">Settings</span>
        </button>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Sidebar — persistent on lg+, drawer on smaller screens */}
        <div className="hidden lg:block">
          <Sidebar
            projects={projects}
            selectedProjectId={selectedProjectId}
            onSelect={handleSelectProject}
            onAdd={async (name, path) => { await addProject(name, path) }}
            onRemove={async (id) => {
              await removeProject(id)
              if (selectedProjectId === id) setSelectedProjectId(null)
            }}
          />
        </div>

        {showSidebar && (
          <div className="lg:hidden fixed inset-0 z-30 flex">
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
              onClick={() => setShowSidebar(false)}
            />
            <div className="relative animate-slide-in-left">
              <Sidebar
                projects={projects}
                selectedProjectId={selectedProjectId}
                onSelect={handleSelectProject}
                onClose={() => setShowSidebar(false)}
                onAdd={async (name, path) => { await addProject(name, path) }}
                onRemove={async (id) => {
                  await removeProject(id)
                  if (selectedProjectId === id) setSelectedProjectId(null)
                }}
              />
            </div>
          </div>
        )}

        {/* Feed */}
        <main className="flex-1 min-w-0 overflow-hidden">
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
          <>
            {/* Mobile backdrop */}
            <div
              className="md:hidden fixed inset-0 z-30 bg-black/60 backdrop-blur-sm animate-fade-in"
              onClick={() => setSelectedReview(null)}
            />
            <div className="fixed md:relative inset-0 md:inset-auto z-40 md:z-auto md:w-[28rem] lg:w-[32rem] md:shrink-0 overflow-hidden animate-slide-in-right">
              <ReviewDetail
                review={selectedReview}
                isStreaming={streamingIds.has(selectedReview.id)}
                onDelete={handleDeleteReview}
                onClose={() => setSelectedReview(null)}
              />
            </div>
          </>
        )}
      </div>

      <StatusBar status={status} />

      {showSettings && <Settings onClose={() => setShowSettings(false)} />}

      <ToastContainer toasts={toasts} onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))} />
    </div>
  )
}
