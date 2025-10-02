#!/bin/bash

# Setup shared components
echo "Setting up shared components..."
./sync-shared.sh

# Array to track all process IDs
declare -a PIDS

# Function to kill all processes on exit
cleanup() {
    echo ""
    echo "Stopping all applications..."

    # Kill all processes in the process group
    for pid in "${PIDS[@]}"; do
        if ps -p $pid > /dev/null 2>&1; then
            echo "Killing process $pid..."
            kill -TERM $pid 2>/dev/null
        fi
    done

    # Also kill any remaining Python and npm processes on these ports
    echo "Cleaning up any remaining processes..."
    pkill -f "python.*app.py" 2>/dev/null
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    lsof -ti:5173 | xargs kill -9 2>/dev/null
    lsof -ti:5573 | xargs kill -9 2>/dev/null

    echo "All applications stopped."
    exit 0
}

# Set up the trap
trap cleanup INT TERM EXIT

# Create a function to prefix output
prefix_output() {
    local prefix=$1
    local color=$2
    while IFS= read -r line; do
        echo -e "${color}[${prefix}]${NC} $line"
    done
}

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Start the backend with prefixed output
echo "Starting backend on port 8000..."
cd backend
python -u app.py 2>&1 | prefix_output "BACKEND" "$RED" &
BACKEND_PID=$!
PIDS+=($BACKEND_PID)

# Wait a moment for the backend to start
sleep 2

# Start main frontend with prefixed output
echo "Starting main frontend on port 5173..."
cd ../merged_frontend/frontend
npm run dev 2>&1 | prefix_output "FRONTEND" "$GREEN" &
MAIN_FRONTEND_PID=$!
PIDS+=($MAIN_FRONTEND_PID)

# Start chat frontend with prefixed output
echo "Starting chat-only frontend on port 5573..."
cd ../embed-frontend
npm run dev 2>&1 | prefix_output "CHAT" "$BLUE" &
CHAT_FRONTEND_PID=$!
PIDS+=($CHAT_FRONTEND_PID)

echo -e "${NC}"
echo "All applications started!"
echo "Main application: http://localhost:5173"
echo "Chat-only application: http://localhost:5573"
echo ""
echo "Press Ctrl+C to stop all applications"
echo ""

# Wait for user to press Ctrl+C
wait