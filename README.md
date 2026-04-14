# CodeWatch

**Local AI code review — watches your files, streams reviews in real time. Your code never leaves your machine.**

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Node](https://img.shields.io/badge/node-18%2B-green)

![screenshot](docs/screenshot.png)

## What it does

CodeWatch watches a project folder for file changes, automatically sends changed files to a local LLM running via [Ollama](https://ollama.com), and streams the code review results to a web dashboard in real time. Everything runs locally — no cloud, no telemetry, your code stays on your machine.

## Features

- **Live file watching** — detects saves instantly, debounces rapid edits
- **Streaming reviews** — tokens appear in the UI as they're generated
- **Works with any Ollama model** — `qwen2.5-coder`, `codellama`, `llama3.2`, or anything you've pulled
- **Diff-aware** — subsequent reviews focus on what changed, not the whole file
- **.gitignore-aware** — respects your project's ignore rules automatically
- **Desktop notifications** — critical and warning alerts via your OS notification system
- **Optional Telegram notifications** — get alerts on your phone
- **Dark UI** — three-column layout: projects | feed | detail
- **Local only** — no internet required after setup

---

## Requirements

- Python 3.10+
- Node.js 18+ and npm
- [Ollama](https://ollama.com) installed and running locally, with at least one model pulled

Pull a model before starting CodeWatch:
```bash
ollama pull qwen2.5-coder:3b   # fast, good for code
ollama pull codellama           # alternative
ollama pull llama3.2            # general purpose
```

CodeWatch works with any model — you choose what to use.

---

## Quick start

**Unix / macOS:**
```bash
git clone https://github.com/<your-username>/codewatch.git
cd codewatch
./install.sh
# Edit config.yaml — set 'model:' to the model you pulled
./start.sh
```

**Windows:**
```bat
git clone https://github.com/<your-username>/codewatch.git
cd codewatch
install.bat
REM Edit config.yaml — set 'model:' to the model you pulled
start.bat
```

Then open **http://localhost:8000** in your browser.

---

## Using CodeWatch

1. **Add a project** — click **+** in the sidebar, enter a name and the full path to your project folder
2. **Edit any file** in that folder — CodeWatch detects the change and queues a review
3. **Watch the review stream** — tokens appear in the feed as the model generates them
4. **Click a review** — the detail panel shows the full review with copy/export/delete options
5. **Manual trigger** — click "Review" next to any file in the file tree, or use the API

Severity is auto-detected from the review text:
- **Critical** (red) — security issues, vulnerabilities
- **Warning** (amber) — bugs, unsafe patterns
- **Suggestion** (blue) — improvements, style

---

## Configuration reference

Edit `config.yaml` after installation. Changes to most settings take effect immediately via the Settings page — no restart needed.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `model` | string | `""` | **Required.** Must match a model you've pulled in Ollama (run `ollama list`) |
| `ollama_url` | string | `http://localhost:11434` | Ollama API base URL |
| `ollama_timeout_seconds` | int | `120` | Per-request timeout |
| `watch_extensions` | list | `.py .js .ts ...` | File extensions to watch |
| `ignore_patterns` | list | `node_modules .git ...` | Path fragments to skip |
| `respect_gitignore` | bool | `true` | Honour `.gitignore` in project root |
| `debounce_seconds` | float | `1.5` | Wait this long after last change before triggering |
| `max_file_lines` | int | `400` | Skip files longer than this |
| `skip_unchanged` | bool | `true` | Skip re-review if file content hasn't changed |
| `review_mode` | string | `auto` | `auto` / `always_full` / `always_diff` |
| `max_concurrency` | int | `1` | Parallel reviews (1 is best for local LLMs) |
| `prompt_max_chars` | int | `16000` | Truncate prompts beyond this length |
| `notifications.desktop` | bool | `true` | Enable desktop notifications |
| `notifications.desktop_severities` | list | `[critical, warning]` | Which severities trigger desktop alerts |
| `notifications.telegram` | bool | `false` | Enable Telegram notifications |
| `notifications.telegram_severities` | list | `[critical]` | Which severities go to Telegram |
| `log_level` | string | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

### Secrets (Telegram token, chat ID)

Store these in `.env`, not `config.yaml`:
```
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## Changing the model

**Via UI:** open Settings, pick from the model dropdown (populated from Ollama), click Save.

**Via config.yaml:** set `model: your-model-name` and save — CodeWatch hot-reloads the config.

The model name must exactly match the tag shown by `ollama list`.

---

## Notifications

**Desktop:** enabled by default via `plyer`. Works on Windows, macOS, and most Linux desktops.

**Telegram:**
1. Create a bot via [@BotFather](https://t.me/BotFather) — copy the token
2. Get your chat ID (send a message to the bot, then check `https://api.telegram.org/bot<TOKEN>/getUpdates`)
3. Add to `.env`:
   ```
   TELEGRAM_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```
4. Enable in Settings or set `notifications.telegram: true` in `config.yaml`

---

## Troubleshooting

**Ollama not running**
```bash
ollama serve   # or launch the Ollama desktop app
```

**Model name mismatch** — run `ollama list` and copy the exact tag (e.g. `qwen2.5-coder:3b`) into `config.yaml`.

**Connection refused on port 11434** — check your firewall and confirm Ollama is listening: `curl http://localhost:11434/api/tags`

**Port 8000 already in use** — edit `start.sh`/`start.bat` and pass `--port 8001` to uvicorn.

**Slow reviews** — try a smaller/quantised model (e.g. `qwen2.5-coder:3b` Q4), or increase `debounce_seconds` to reduce review frequency.

**Reviews not triggering** — check that the file extension is in `watch_extensions` and the path isn't matched by `ignore_patterns` or `.gitignore`.

---

## Docker

```bash
cp config.example.yaml config.yaml
# edit config.yaml
docker compose up --build
```

Ollama must be running on the host. The container reaches it via `host.docker.internal:11434`.

---

## Contributing

PRs and issues welcome. Please open an issue before working on large changes.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Acknowledgements

[Ollama](https://ollama.com) · [FastAPI](https://fastapi.tiangolo.com) · [React](https://react.dev) · [Vite](https://vitejs.dev) · [Tailwind CSS](https://tailwindcss.com) · [watchdog](https://github.com/gorakhargosh/watchdog)
