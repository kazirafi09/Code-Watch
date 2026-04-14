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
      <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60">
        <div className="bg-gray-900 rounded p-6 text-gray-400 text-sm">Loading...</div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-gray-900 border border-gray-700 rounded-lg w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-200">Settings</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white">×</button>
        </div>

        <form onSubmit={handleSave} className="p-5 flex flex-col gap-5">
          {/* Model */}
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Model</h3>
            {modelsAvailable && models.length > 0 ? (
              <select
                value={config.model}
                onChange={(e) => set('model', e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-100 focus:outline-none focus:border-blue-500"
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
                className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            )}
            <p className="text-xs text-gray-600 mt-1">Must match a model you've pulled in Ollama.</p>
          </section>

          {/* Watch settings */}
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Watching</h3>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1">
                <span className="text-xs text-gray-500">Debounce (seconds)</span>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={config.debounce_seconds}
                  onChange={(e) => set('debounce_seconds', parseFloat(e.target.value))}
                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-100 focus:outline-none focus:border-blue-500"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-gray-500">Max file lines</span>
                <input
                  type="number"
                  min="1"
                  value={config.max_file_lines}
                  onChange={(e) => set('max_file_lines', parseInt(e.target.value))}
                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-100 focus:outline-none focus:border-blue-500"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-gray-500">Max concurrency</span>
                <input
                  type="number"
                  min="1"
                  max="4"
                  value={config.max_concurrency}
                  onChange={(e) => set('max_concurrency', parseInt(e.target.value))}
                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-100 focus:outline-none focus:border-blue-500"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-gray-500">Review mode</span>
                <select
                  value={config.review_mode}
                  onChange={(e) => set('review_mode', e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-100 focus:outline-none focus:border-blue-500"
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
            <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Notifications</h3>
            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 text-xs text-gray-300">
                <input
                  type="checkbox"
                  checked={config.notifications.desktop}
                  onChange={(e) => set('notifications', { ...config.notifications, desktop: e.target.checked })}
                  className="accent-blue-500"
                />
                Desktop notifications
              </label>
              <label className="flex items-center gap-2 text-xs text-gray-300">
                <input
                  type="checkbox"
                  checked={config.notifications.telegram}
                  onChange={(e) => set('notifications', { ...config.notifications, telegram: e.target.checked })}
                  className="accent-blue-500"
                />
                Telegram notifications
              </label>
              {config.notifications.telegram && (
                <div className="ml-5 flex flex-col gap-2">
                  <input
                    type="password"
                    placeholder="Telegram bot token"
                    value={config.notifications.telegram_token === '***' ? '' : config.notifications.telegram_token}
                    onChange={(e) => set('notifications', { ...config.notifications, telegram_token: e.target.value })}
                    className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  />
                  <input
                    type="text"
                    placeholder="Telegram chat ID"
                    value={config.notifications.telegram_chat_id === '***' ? '' : config.notifications.telegram_chat_id}
                    onChange={(e) => set('notifications', { ...config.notifications, telegram_chat_id: e.target.value })}
                    className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
                  />
                  <p className="text-xs text-gray-600">Secrets are stored in .env, not config.yaml.</p>
                </div>
              )}
            </div>
          </section>

          {error && <p className="text-red-400 text-xs">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="bg-blue-700 hover:bg-blue-600 text-white text-xs rounded px-4 py-2 disabled:opacity-50"
            >
              {saving ? 'Saving...' : saved ? 'Saved!' : 'Save'}
            </button>
            <button type="button" onClick={onClose} className="text-xs text-gray-500 hover:text-gray-300 px-4 py-2">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
