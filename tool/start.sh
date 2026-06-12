#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Source optionnelle des secrets de la base distante latelier (gitignoré).
if [ -f "$SCRIPT_DIR/.env.latelier" ]; then
  set -a; . "$SCRIPT_DIR/.env.latelier"; set +a
  echo "  (source distante latelier : .env.latelier chargé)"
fi

echo "Starting backend on http://localhost:8000 ..."
PYTHONPATH=. .venv/bin/uvicorn backend.main:app --port 8000 --reload &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:5173 ..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend PID: $BACKEND_PID"
echo "  Frontend PID: $FRONTEND_PID"
echo ""
echo "  App: http://localhost:5173"
echo "  API: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop."

wait
