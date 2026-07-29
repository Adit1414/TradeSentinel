#!/usr/bin/env bash

# Trap SIGINT and SIGTERM to kill both background processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping TradingHelper Backend and Frontend..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo "🚀 Starting TradingHelper..."

# Start Backend
cd "$DIR/backend" || exit 1
echo "Starting Backend (http://localhost:8000)..."
conda run -n ai uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start Frontend
cd "$DIR/frontend" || exit 1
echo "Starting Frontend (http://localhost:5173)..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Both servers are running!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop both servers."
echo ""

wait
