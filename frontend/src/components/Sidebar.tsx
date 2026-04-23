import { useState } from 'react'
import type { Project } from '../api/types'

interface Props {
  projects: Project[]
  selectedProjectId: number | null
  onSelect: (id: number | null) => void
  onAdd: (name: string, path: string) => Promise<void>
  onRemove: (id: number) => Promise<void>
  onClose?: () => void
}

export function Sidebar({ projects, selectedProjectId, onSelect, onAdd, onRemove, onClose }: Props) {
  const [showAdd, setShowAdd] = useState(false)
  const [name, setName] = useState('')
  const [path, setPath] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !path.trim()) return
    setAdding(true)
    setError('')
    try {
      await onAdd(name.trim(), path.trim())
      setName('')
      setPath('')
      setShowAdd(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add project')
    } finally {
      setAdding(false)
    }
  }

  return (
    <aside className="w-72 h-full shrink-0 flex flex-col bg-surface-1 border-r border-white/5 overflow-hidden">
      <div className="px-4 h-14 border-b border-white/5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Projects</span>
          <span className="chip bg-white/5 text-slate-400 border border-white/5">{projects.length}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowAdd((v) => !v)}
            className="btn-ghost p-1.5"
            title={showAdd ? 'Cancel' : 'Add project'}
            aria-label="Add project"
          >
            {showAdd ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
            )}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="lg:hidden btn-ghost p-1.5"
              aria-label="Close sidebar"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          )}
        </div>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="p-4 border-b border-white/5 flex flex-col gap-2 bg-surface-2/40 animate-fade-in">
          <input
            placeholder="Project name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input text-xs py-1.5"
            autoFocus
          />
          <input
            placeholder="Folder path"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            className="input text-xs py-1.5 font-mono"
          />
          {error && <p className="text-rose-400 text-xs">{error}</p>}
          <button type="submit" disabled={adding} className="btn-primary justify-center">
            {adding ? 'Adding...' : 'Add project'}
          </button>
        </form>
      )}

      <nav className="flex-1 overflow-y-auto p-2 flex flex-col gap-0.5">
        <button
          onClick={() => onSelect(null)}
          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center gap-2 ${
            selectedProjectId === null
              ? 'bg-accent-500/15 text-accent-400 border border-accent-500/25'
              : 'text-slate-300 hover:bg-white/5 border border-transparent'
          }`}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
          All projects
        </button>

        {projects.map((p) => (
          <div
            key={p.id}
            className={`group flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors border ${
              selectedProjectId === p.id
                ? 'bg-accent-500/15 text-accent-400 border-accent-500/25'
                : 'text-slate-300 hover:bg-white/5 border-transparent'
            }`}
            onClick={() => onSelect(p.id)}
          >
            <div className="flex items-center gap-2 min-w-0">
              <span
                className={`w-2 h-2 rounded-full shrink-0 ${p.is_watching ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]' : 'bg-slate-600'}`}
                title={p.is_watching ? 'Watching' : 'Not watching'}
              />
              <span className="truncate text-sm">{p.name}</span>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); onRemove(p.id) }}
              className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-400 transition-opacity shrink-0 p-0.5"
              title="Remove project"
              aria-label={`Remove ${p.name}`}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
              </svg>
            </button>
          </div>
        ))}

        {projects.length === 0 && !showAdd && (
          <div className="mt-8 px-4 text-center">
            <div className="mx-auto w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center mb-3">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <p className="text-sm text-slate-300 mb-1">No projects yet</p>
            <p className="text-xs text-slate-500">Click + to add a folder to watch.</p>
          </div>
        )}
      </nav>
    </aside>
  )
}
