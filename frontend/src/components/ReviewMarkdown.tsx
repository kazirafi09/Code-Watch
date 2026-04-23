import ReactMarkdown, { type Components } from 'react-markdown'
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'

const SEVERITY_PATTERNS: Array<{ re: RegExp; cls: string }> = [
  { re: /\b(critical|security|vulnerability|exploit|injection)\b/gi, cls: 'text-rose-400 font-semibold' },
  { re: /\b(warning|bug|error|unsafe|deprecated)\b/gi, cls: 'text-amber-400' },
  { re: /\b(suggestion|recommend|consider|improve)\b/gi, cls: 'text-sky-400' },
]

function highlightTextNodes(text: string): React.ReactNode {
  const parts: Array<{ start: number; end: number; cls: string }> = []
  for (const { re, cls } of SEVERITY_PATTERNS) {
    re.lastIndex = 0
    let m: RegExpExecArray | null
    while ((m = re.exec(text)) !== null) {
      parts.push({ start: m.index, end: m.index + m[0].length, cls })
    }
  }
  if (parts.length === 0) return text
  parts.sort((a, b) => a.start - b.start)
  const out: React.ReactNode[] = []
  let cursor = 0
  for (const p of parts) {
    if (p.start < cursor) continue
    if (p.start > cursor) out.push(text.slice(cursor, p.start))
    out.push(
      <span key={`${p.start}-${p.end}`} className={p.cls}>
        {text.slice(p.start, p.end)}
      </span>,
    )
    cursor = p.end
  }
  if (cursor < text.length) out.push(text.slice(cursor))
  return <>{out}</>
}

function highlightChildren(children: React.ReactNode): React.ReactNode {
  if (typeof children === 'string') return highlightTextNodes(children)
  if (Array.isArray(children)) {
    return children.map((c, i) =>
      typeof c === 'string' ? <span key={i}>{highlightTextNodes(c)}</span> : c,
    )
  }
  return children
}

const components: Components = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{highlightChildren(children)}</p>,
  li: ({ children }) => <li>{highlightChildren(children)}</li>,
  h1: ({ children }) => <h1 className="text-base font-semibold mt-3 mb-1">{highlightChildren(children)}</h1>,
  h2: ({ children }) => <h2 className="text-sm font-semibold mt-3 mb-1">{highlightChildren(children)}</h2>,
  h3: ({ children }) => <h3 className="text-sm font-semibold mt-2 mb-1">{highlightChildren(children)}</h3>,
  ul: ({ children }) => <ul className="list-disc pl-5 mb-2">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-5 mb-2">{children}</ol>,
  code: ({ className, children }) => {
    const isBlock = className?.startsWith('language-')
    if (isBlock) {
      return (
        <code className="block font-mono bg-surface-0 border border-white/10 rounded-lg px-3 py-2 text-xs overflow-x-auto leading-relaxed">
          {children}
        </code>
      )
    }
    return <code className="font-mono bg-white/10 rounded px-1.5 py-0.5 text-[0.85em] text-slate-200">{children}</code>
  },
  pre: ({ children }) => <pre className="mb-2">{children}</pre>,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer noopener" className="text-accent-400 hover:text-accent-300 underline underline-offset-2">
      {children}
    </a>
  ),
}

interface Props {
  text: string
  className?: string
}

export function ReviewMarkdown({ text, className }: Props) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, defaultSchema]]}
        components={components}
      >
        {text}
      </ReactMarkdown>
    </div>
  )
}
