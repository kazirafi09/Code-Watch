#!/usr/bin/env bash
set -e

echo "Installing CodeWatch..."
echo ""
echo "Reminder: install Ollama separately from https://ollama.com and pull any model you like."
echo "  Example: ollama pull qwen2.5-coder:3b"
echo "Then set the model name in config.yaml."
echo ""

# Check Python 3.10+
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Please install Python 3.10+." >&2
    exit 1
fi
PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")
if [ "$PYTHON_VER" -lt "310" ]; then
    echo "ERROR: Python 3.10+ required (found $(python3 --version))." >&2
    exit 1
fi

# Check Node 18+
if ! command -v node &>/dev/null; then
    echo "ERROR: node not found. Please install Node.js 18+." >&2
    exit 1
fi
NODE_VER=$(node -e "process.stdout.write(process.versions.node.split('.')[0])")
if [ "$NODE_VER" -lt "18" ]; then
    echo "ERROR: Node.js 18+ required (found node $NODE_VER)." >&2
    exit 1
fi

# Check npm
if ! command -v npm &>/dev/null; then
    echo "ERROR: npm not found. Please install npm." >&2
    exit 1
fi

# Python venv + deps
echo "Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Frontend
echo "Building frontend..."
cd frontend
npm install --silent
npm run build
cd ..

# First-run config
[ -f config.yaml ] || cp config.example.yaml config.yaml
[ -f .env ] || cp .env.example .env

echo ""
echo "Done! Edit config.yaml and set 'model:' to a model you've pulled in Ollama."
echo "Then run ./start.sh to launch CodeWatch."
