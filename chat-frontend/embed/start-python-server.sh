#!/bin/bash

# Get the current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Starting Python HTTP server for Sapientum AI Embed..."
echo "Server will be available at: http://localhost:7000"
echo "Press Ctrl+C to stop the server"

# Run the Python server script
python3 "$DIR/server.py"