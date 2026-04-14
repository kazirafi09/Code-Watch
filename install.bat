@echo off
setlocal enabledelayedexpansion

echo Installing CodeWatch...
echo.
echo Reminder: install Ollama separately from https://ollama.com and pull any model you like.
echo   Example: ollama pull qwen2.5-coder:3b
echo Then set the model name in config.yaml.
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+.
    exit /b 1
)

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Please install Node.js 18+.
    exit /b 1
)

REM Check npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm not found. Please install npm.
    exit /b 1
)

echo Creating Python virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo Building frontend...
cd frontend
call npm install --silent
call npm run build
cd ..

if not exist config.yaml copy config.example.yaml config.yaml
if not exist .env copy .env.example .env

echo.
echo Done! Edit config.yaml and set 'model:' to a model you've pulled in Ollama.
echo Then run start.bat to launch CodeWatch.
endlocal
