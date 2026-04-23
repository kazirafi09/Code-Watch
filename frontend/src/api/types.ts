export interface Project {
  id: number
  name: string
  path: string
  created_at: string
  is_active: boolean
  is_watching: boolean
}

export interface Review {
  id: string
  project_id: number
  filename: string
  language: string
  full_text: string
  severity: 'critical' | 'warning' | 'suggestion' | 'pending'
  mode: 'full' | 'diff' | 'full+diff'
  prompt_tokens: number
  completion_tokens: number
  duration_ms: number
  created_at: string
}

export interface ReviewsResponse {
  items: Review[]
  total: number
  limit: number
  offset: number
}

export interface StatusResponse {
  ollama_ok: boolean
  model: string
  queue_depth: number
  pending_reviews: number
  last_duration_ms: number | null
  tokens_per_sec: number | null
}

export interface ModelsResponse {
  models: string[]
  available: boolean
}

export interface AppConfig {
  model: string
  ollama_url: string
  ollama_timeout_seconds: number
  watch_extensions: string[]
  ignore_patterns: string[]
  respect_gitignore: boolean
  debounce_seconds: number
  max_file_lines: number
  skip_unchanged: boolean
  review_mode: string
  max_concurrency: number
  prompt_max_chars: number
  notifications: {
    desktop: boolean
    desktop_severities: string[]
    telegram: boolean
    telegram_severities: string[]
    telegram_token: string
    telegram_chat_id: string
  }
  log_level: string
}

// WebSocket event types
export type WsEvent =
  | { type: 'review_start'; review_id: string; project_id: number; filename: string; timestamp: string }
  | { type: 'review_token'; review_id: string; token: string }
  | { type: 'review_done'; review_id: string; full_text: string; severity: string; mode: 'full' | 'diff' | 'full+diff' }
  | { type: 'queue_update'; depth: number }
  | { type: 'status_update'; ollama_ok: boolean; model: string; queue_depth: number; last_duration_ms: number | null; tokens_per_sec: number | null }
  | { type: 'toast'; level: 'error' | 'warning' | 'info' | 'success'; message: string }
