import { useState } from 'react'
import type { Project } from '../api/types'

interface Props {
  projects: Project[]
  selectedProjectId: number | null
  onSelect: (id: number | null) => void
  onAdd: (name: string, path: string) => Promise<void>
  onRemove: (id: number) => Promise<void>
}

export function Sidebar({ projects, selectedProjectId, onSelect, onAdd, onRemove }: Props) {
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
    <aside className="w-56 shrink-0 flex flex-col bg-gray-900 border-r border-gray-800 overflow-hidden">
      <div className="px-3 py-3 border-b border-gray-800 flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-300">Projects</span>
        <button
          onClick={() => setShowAdd((v) => !v)}
          className="text-gray-400 hover:text-white text-lg leading-none"
          title="Add project"
        >
          {showAdd ? '×' : '+'}
        </button>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="p-3 border-b border-gray-800 flex flex-col gap-2">
          <input
            placeholder="Project name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <input
            placeholder="Folder path"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          {error && <p className="text-red-400 text-xs">{error}</p>}
          <button
            type="submit"
            disabled={adding}
            className="bg-blue-700 hover:bg-blue-600 text-white text-xs rounded py-1 disabled:opacity-50"
          >
            {adding ? 'Adding...' : 'Add'}
          </button>
        </form>
      )}

      <nav className="flex-1 overflow-y-auto py-1">
        <button
          onClick={() => onSelect(null)}
          className={`w-full text-left px-3 py-2 text-xs rounded-none transition-colors ${
            selectedProjectId === null
              ? 'bg-gray-700 text-white'
              : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
          }`}
        >
          All projects
        </button>
        {projects.map((p) => (
          <div
            key={p.id}
            className={`group flex items-center justify-between px-3 py-2 cursor-pointer transition-colors ${
              selectedProjectId === p.id
                ? 'bg-gray-700 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
            }`}
            onClick={() => onSelect(p.id)}
          >
            <div className="flex items-center gap-1.5 min-w-0">
              <span
                className={`w-1.5 h-1.5 rounded-full shrink-0 ${p.is_watching ? 'bg-green-500' : 'bg-gray-600'}`}
                title={p.is_watching ? 'Watching' : 'Not watching'}
              />
              <span className="truncate text-xs">{p.name}</span>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); onRemove(p.id) }}
              className="opacity-0 group-hover:opacity-60 hover:!opacity-100 text-red-400 text-sm ml-1 shrink-0"
              title="Remove project"
            >
              ×
            </button>
          </div>
        ))}
        {projects.length === 0 && !showAdd && (
          <p className="px-3 py-4 text-xs text-gray-600 text-center">
            No projects yet.<br />Click + to add one.
          </p>
        )}
      </nav>
    </aside>
  )
}
