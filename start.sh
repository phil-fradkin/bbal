#!/bin/bash

echo "Starting NBA Auction Value Calculator..."

# Start backend
echo "Starting backend server..."
cd backend
python -m pip install -r requirements.txt --quiet
python main.py &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting frontend..."
cd ../frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "========================================"
echo "NBA Auction Value Calculator is running!"
echo "========================================"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for interrupt
trap "echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait