#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping servers..."
    kill $(jobs -p) 2>/dev/null
}

trap cleanup EXIT

echo "Starting Backend Server..."
# Activate venv and run uvicorn
source .venv/bin/activate
uvicorn backend.app.api:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Starting Frontend Server..."
# Run python http server
cd frontend
python3 -m http.server 8080 &
FRONTEND_PID=$!
cd ..

echo "Vidhi-Sahayak is running!"
echo "Frontend: http://localhost:8080/pages/index.html"
echo "Backend: http://localhost:8000"
echo "Press Ctrl+C to stop."

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
