#!/bin/bash
echo "============================================"
echo "  Gmail Client - Starting..."
echo "============================================"
echo

# Install backend dependencies
echo "[1/2] Installing Python dependencies..."
cd backend
pip install -r requirements.txt -q
cd ..

# Install frontend dependencies
echo "[2/2] Installing frontend dependencies..."
cd frontend
npm install --silent
cd ..

# Start both servers
echo
echo "Starting servers..."
echo "  Backend:  http://127.0.0.1:8000"
echo "  Frontend: http://localhost:3000"
echo

cd backend && python main.py &
BACKEND_PID=$!
cd ..
sleep 2

cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo
echo "Open http://localhost:3000 in your browser"
echo "Press Ctrl+C to stop both servers"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
