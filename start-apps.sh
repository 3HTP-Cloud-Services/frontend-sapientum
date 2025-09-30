#!/bin/bash

# Setup shared components
echo "Setting up shared components..."
./sync-shared.sh

# Start the backend
echo "Starting backend on port 8000..."
cd backend
python app.py &
BACKEND_PID=$!

# Wait a moment for the backend to start
sleep 2

# Update vite.config.js in frontend apps to use the correct path
echo "Starting main frontend on port 5173..."
cd ../merged_frontend/frontend
npm run dev &
MAIN_FRONTEND_PID=$!

echo "Starting chat-only frontend on port 5573..."
cd ../embed-frontend
npm run dev &
CHAT_FRONTEND_PID=$!

echo "All applications started!"
echo "Main application: http://localhost:5173"
echo "Chat-only application: http://localhost:5573"
echo ""
echo "Press Ctrl+C to stop all applications"

# Function to kill all processes on exit
cleanup() {
    echo "Stopping all applications..."
    kill $BACKEND_PID 2>/dev/null
    kill $MAIN_FRONTEND_PID 2>/dev/null
    kill $CHAT_FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up the trap
trap cleanup INT TERM

# Wait for user to press Ctrl+C
wait