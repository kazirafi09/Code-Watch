# /dev — Start dev servers

Start both the backend and frontend dev servers.

## Backend
```bash
source .venv/bin/activate  # Unix
# .venv/Scripts/activate   # Windows
uvicorn backend.main:app --reload --port 8000
```

## Frontend (separate terminal)
```bash
cd frontend
npm run dev
# Vite at http://localhost:5173 (proxies API calls to :8000)
```

Run both in parallel terminals. Backend must be up before frontend makes API calls.
