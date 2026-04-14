#!/usr/bin/env bash
set -e

if [ ! -d ".venv" ]; then
    echo "ERROR: .venv not found. Run ./install.sh first." >&2
    exit 1
fi

if [ ! -f "config.yaml" ]; then
    cp config.example.yaml config.yaml
    echo "Created config.yaml from template. Set 'model:' before running."
fi

echo "Starting CodeWatch..."
source .venv/bin/activate

uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
PID=$!
sleep 2

xdg-open http://localhost:8000 2>/dev/null || \
open http://localhost:8000 2>/dev/null || \
echo "Open http://localhost:8000 in your browser"

echo "CodeWatch running (PID $PID). Press Ctrl+C to stop."
wait $PID
