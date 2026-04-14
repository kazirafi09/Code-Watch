export type Severity = 'critical' | 'warning' | 'suggestion' | 'pending'

export function severityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'text-red-400'
    case 'warning': return 'text-amber-400'
    case 'suggestion': return 'text-blue-400'
    default: return 'text-gray-400'
  }
}

export function severityBg(severity: string): string {
  switch (severity) {
    case 'critical': return 'bg-red-900/40 border-red-700'
    case 'warning': return 'bg-amber-900/40 border-amber-700'
    case 'suggestion': return 'bg-blue-900/40 border-blue-700'
    default: return 'bg-gray-800 border-gray-700'
  }
}

export function severityBadge(severity: string): string {
  switch (severity) {
    case 'critical': return 'bg-red-700 text-red-100'
    case 'warning': return 'bg-amber-700 text-amber-100'
    case 'suggestion': return 'bg-blue-700 text-blue-100'
    default: return 'bg-gray-700 text-gray-100'
  }
}
