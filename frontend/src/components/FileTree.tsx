import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Project } from '../api/types'

interface TreeNode {
  name: string
  path: string
  is_dir: boolean
  children?: TreeNode[]
}

interface Props {
  project: Project
}

function TreeItem({ node, projectId, depth }: { node: TreeNode; projectId: number; depth: number }) {
  const [expanded, setExpanded] = useState(depth < 1)
  const [triggering, setTriggering] = useState(false)

  const handleTrigger = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setTriggering(true)
    try {
      await api.triggerReview(projectId, node.path)
    } finally {
      setTriggering(false)
    }
  }

  if (node.is_dir) {
    return (
      <div>
        <div
          className="flex items-center gap-1 px-2 py-0.5 cursor-pointer hover:bg-gray-800 text-xs text-gray-400 group"
          style={{ paddingLeft: `${8 + depth * 12}px` }}
          onClick={() => setExpanded((v) => !v)}
        >
          <span className="text-gray-600">{expanded ? '▾' : '▸'}</span>
          <span className="truncate">{node.name}/</span>
        </div>
        {expanded && node.children?.map((child) => (
          <TreeItem key={child.path} node={child} projectId={projectId} depth={depth + 1} />
        ))}
      </div>
    )
  }

  return (
    <div
      className="flex items-center justify-between px-2 py-0.5 hover:bg-gray-800 text-xs text-gray-300 group"
      style={{ paddingLeft: `${8 + depth * 12}px` }}
    >
      <span className="truncate">{node.name}</span>
      <button
        onClick={handleTrigger}
        disabled={triggering}
        className="opacity-0 group-hover:opacity-60 hover:!opacity-100 text-blue-400 text-xs ml-2 shrink-0 disabled:opacity-30"
      >
        {triggering ? '...' : 'Review'}
      </button>
    </div>
  )
}

export function FileTree({ project }: Props) {
  const [tree, setTree] = useState<TreeNode[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // Build a simple tree by listing what the backend might expose
    // For now we make a best-effort client-side display using the project path
    setLoading(false)
    setTree([])
  }, [project.id])

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-gray-800 text-xs text-gray-400 font-semibold shrink-0">
        {project.name}
      </div>
      <div className="flex-1 overflow-y-auto py-1">
        {loading && <div className="text-xs text-gray-600 p-3">Loading...</div>}
        {!loading && tree.length === 0 && (
          <div className="text-xs text-gray-600 p-3">
            Use "Review now" via the feed, or edit a file to auto-trigger a review.
          </div>
        )}
        {tree.map((node) => (
          <TreeItem key={node.path} node={node} projectId={project.id} depth={0} />
        ))}
      </div>
    </div>
  )
}
