export type Severity = 'critical' | 'warning' | 'suggestion' | 'pending'

export function severityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'text-rose-400'
    case 'warning': return 'text-amber-400'
    case 'suggestion': return 'text-sky-400'
    default: return 'text-slate-400'
  }
}

export function severityBg(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'bg-gradient-to-br from-rose-500/10 to-rose-500/[0.02] border-rose-500/25'
    case 'warning':
      return 'bg-gradient-to-br from-amber-500/10 to-amber-500/[0.02] border-amber-500/25'
    case 'suggestion':
      return 'bg-gradient-to-br from-sky-500/10 to-sky-500/[0.02] border-sky-500/25'
    default:
      return 'bg-surface-1 border-white/10'
  }
}

export function severityBadge(severity: string): string {
  switch (severity) {
    case 'critical': return 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
    case 'warning': return 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
    case 'suggestion': return 'bg-sky-500/15 text-sky-300 border border-sky-500/30'
    default: return 'bg-slate-500/15 text-slate-300 border border-slate-500/30'
  }
}

export function severityDot(severity: string): string {
  switch (severity) {
    case 'critical': return 'bg-rose-400'
    case 'warning': return 'bg-amber-400'
    case 'suggestion': return 'bg-sky-400'
    default: return 'bg-slate-500'
  }
}
