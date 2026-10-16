#!/usr/bin/env bash
# ==============================================================================
# macOS RAG Research Workspace - Unified Launch Script
# Starts FastAPI backend (port 8000) and Vite React frontend (port 5173)
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "=========================================================="
echo "  🚀 Starting macOS RAG Research Workspace"
echo "  Architecture: Apple Silicon / Intel macOS"
echo "=========================================================="

# 1. Check Python installation
if [ -f "$BACKEND_DIR/venv/bin/python" ]; then
    PYTHON_CMD="$BACKEND_DIR/venv/bin/python"
elif command -v python3.11 &>/dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    echo "❌ Error: Python 3 is not installed. Please install Python 3.11+."
    exit 1
fi

# 2. Check Node.js installation
if ! command -v node &>/dev/null; then
    echo "❌ Error: Node.js is not installed. Please install Node.js 18+."
    exit 1
fi

# 3. Setup Virtualenv if not present
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "📦 Creating Python virtual environment in $BACKEND_DIR/venv..."
    $PYTHON_CMD -m venv "$BACKEND_DIR/venv"
    "$BACKEND_DIR/venv/bin/pip" install --upgrade pip
    echo "📥 Installing backend requirements..."
    "$BACKEND_DIR/venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
fi

# 4. Setup Frontend node_modules if not present
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    (cd "$FRONTEND_DIR" && npm install)
fi

# 5. Trap signals to cleanly terminate background jobs on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down macOS RAG services..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    echo "✅ Shutdown complete. Goodbye!"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 6. Start Backend (FastAPI + Uvicorn)
echo "⚡ Starting FastAPI backend on http://localhost:8000 ..."
(
    cd "$BACKEND_DIR"
    "$BACKEND_DIR/venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 --reload
) &
BACKEND_PID=$!

# Wait briefly for backend to initialize
sleep 2

# 7. Start Frontend (Vite)
echo "⚡ Starting React frontend on http://localhost:5173 ..."
(
    cd "$FRONTEND_DIR"
    npm run dev -- --host 0.0.0.0 --port 5173
) &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo "  🎉 Application is ready!"
echo "  👉 Open your browser at: http://localhost:5173"
echo "  👉 FastAPI Docs:         http://localhost:8000/docs"
echo "  👉 Press Ctrl+C anytime to stop both servers."
echo "=========================================================="
echo ""

# Wait for background jobs
wait
