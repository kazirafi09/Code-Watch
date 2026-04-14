@echo off
setlocal

if not exist .venv (
    echo ERROR: .venv not found. Run install.bat first.
    exit /b 1
)

if not exist config.yaml (
    copy config.example.yaml config.yaml
    echo Created config.yaml from template. Set 'model:' before running.
)

echo Starting CodeWatch...
call .venv\Scripts\activate.bat

start "" http://localhost:8000
uvicorn backend.main:app --host 0.0.0.0 --port 8000

endlocal
