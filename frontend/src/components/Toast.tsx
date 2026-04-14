import { useEffect } from 'react'

export interface ToastMessage {
  id: string
  level: 'error' | 'warning' | 'info' | 'success'
  message: string
}

interface Props {
  toasts: ToastMessage[]
  onDismiss: (id: string) => void
}

const levelStyles: Record<string, string> = {
  error: 'bg-red-900 border-red-600 text-red-100',
  warning: 'bg-amber-900 border-amber-600 text-amber-100',
  info: 'bg-blue-900 border-blue-600 text-blue-100',
  success: 'bg-green-900 border-green-600 text-green-100',
}

function ToastItem({ toast, onDismiss }: { toast: ToastMessage; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000)
    return () => clearTimeout(timer)
  }, [onDismiss])

  return (
    <div
      className={`flex items-start gap-2 px-4 py-3 rounded border text-sm max-w-sm shadow-lg ${levelStyles[toast.level] ?? levelStyles.info}`}
    >
      <span className="flex-1 break-words">{toast.message}</span>
      <button onClick={onDismiss} className="opacity-60 hover:opacity-100 shrink-0">×</button>
    </div>
  )
}

export function ToastContainer({ toasts, onDismiss }: Props) {
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={() => onDismiss(t.id)} />
      ))}
    </div>
  )
}
