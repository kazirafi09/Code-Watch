import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { AppConfig } from '../api/types'

interface Props {
  onClose: () => void
}

export function Settings({ onClose }: Props) {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [models, setModels] = useState<string[]>([])
  const [modelsAvailable, setModelsAvailable] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.getConfig(), api.getModels()]).then(([cfg, mods]) => {
      setConfig(cfg)
      setModels(mods.models)
      setModelsAvailable(mods.available)
    })
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!config) return
    setSaving(true)
    setError('')
    try {
      await api.updateConfig(config)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const set = <K extends keyof AppConfig>(key: K, value: AppConfig[K]) => {
    setConfig((prev) => prev ? { ...prev, [key]: value } : null)
  }

  if (!config) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-fade-in">
        <div className="card p-6 text-slate-400 text-sm flex items-center gap-3">
          <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="2" x2="12" y2="6" />
            <line x1="12" y1="18" x2="12" y2="22" />
            <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
            <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
            <line x1="2" y1="12" x2="6" y2="12" />
            <line x1="18" y1="12" x2="22" y2="12" />
          </svg>
          Loading settings...
        </div>
      </div>
    )
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-surface-1 border border-white/10 rounded-2xl w-full max-w-xl max-h-[90vh] overflow-hidden shadow-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 h-14 border-b border-white/5 shrink-0">
          <div className="flex items-center gap-2">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-accent-400">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            <h2 className="text-base font-semibold text-slate-100">Settings</h2>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5" aria-label="Close settings">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSave} className="overflow-y-auto flex-1">
          <div className="p-6 flex flex-col gap-6">
            {/* Model */}
            <section>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Model</h3>
              {modelsAvailable && models.length > 0 ? (
                <select
                  value={config.model}
                  onChange={(e) => set('model', e.target.value)}
                  className="input"
                >
                  <option value="">Select a model...</option>
                  {models.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              ) : (
                <input
                  type="text"
                  value={config.model}
                  onChange={(e) => set('model', e.target.value)}
                  placeholder={modelsAvailable ? 'No models found — type manually' : 'Ollama offline — type manually'}
                  className="input font-mono"
                />
              )}
              <p className="text-xs text-slate-500 mt-2">Must match a model you've pulled in Ollama.</p>
            </section>

            {/* Watch settings */}
            <section>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Watching</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs text-slate-400">Debounce (seconds)</span>
                  <input
                    type="number"
                    step="0.1"
                    min="0.1"
                    value={config.debounce_seconds}
                    onChange={(e) => set('debounce_seconds', parseFloat(e.target.value))}
                    className="input"
                  />
                </label>
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs text-slate-400">Max file lines</span>
                  <input
                    type="number"
                    min="1"
                    value={config.max_file_lines}
                    onChange={(e) => set('max_file_lines', parseInt(e.target.value))}
                    className="input"
                  />
                </label>
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs text-slate-400">Max concurrency</span>
                  <input
                    type="number"
                    min="1"
                    max="4"
                    value={config.max_concurrency}
                    onChange={(e) => set('max_concurrency', parseInt(e.target.value))}
                    className="input"
                  />
                </label>
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs text-slate-400">Review mode</span>
                  <select
                    value={config.review_mode}
                    onChange={(e) => set('review_mode', e.target.value)}
                    className="input"
                  >
                    <option value="auto">auto</option>
                    <option value="always_full">always_full</option>
                    <option value="always_diff">always_diff</option>
                  </select>
                </label>
              </div>
            </section>

            {/* Notifications */}
            <section>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Notifications</h3>
              <div className="flex flex-col gap-2">
                <label className="flex items-center gap-2.5 text-sm text-slate-200 py-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.notifications.desktop}
                    onChange={(e) => set('notifications', { ...config.notifications, desktop: e.target.checked })}
                    className="w-4 h-4 accent-accent-500"
                  />
                  Desktop notifications
                </label>
                <label className="flex items-center gap-2.5 text-sm text-slate-200 py-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.notifications.telegram}
                    onChange={(e) => set('notifications', { ...config.notifications, telegram: e.target.checked })}
                    className="w-4 h-4 accent-accent-500"
                  />
                  Telegram notifications
                </label>
                {config.notifications.telegram && (
                  <div className="ml-7 mt-1 flex flex-col gap-2 animate-fade-in">
                    <input
                      type="password"
                      placeholder="Telegram bot token"
                      value={config.notifications.telegram_token === '***' ? '' : config.notifications.telegram_token}
                      onChange={(e) => set('notifications', { ...config.notifications, telegram_token: e.target.value })}
                      className="input font-mono text-xs"
                    />
                    <input
                      type="text"
                      placeholder="Telegram chat ID"
                      value={config.notifications.telegram_chat_id === '***' ? '' : config.notifications.telegram_chat_id}
                      onChange={(e) => set('notifications', { ...config.notifications, telegram_chat_id: e.target.value })}
                      className="input font-mono text-xs"
                    />
                    <p className="text-xs text-slate-500">Secrets are stored in .env, not config.yaml.</p>
                  </div>
                )}
              </div>
            </section>

            {error && (
              <p className="text-rose-400 text-xs bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
          </div>

          <div className="flex gap-2 px-6 py-4 border-t border-white/5 bg-surface-2/30 shrink-0">
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? 'Saving...' : saved ? '✓ Saved' : 'Save changes'}
            </button>
            <button type="button" onClick={onClose} className="btn-ghost">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
