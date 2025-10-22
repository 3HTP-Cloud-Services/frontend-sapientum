#!/bin/bash

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "Nginx is not installed. Please install it first or use the Python server instead."
    echo "Run: ./start-python-server.sh"
    exit 1
fi

# Check if nginx is already running
nginx_pid=$(pgrep -f "nginx: master process" || echo "")
if [ -n "$nginx_pid" ]; then
    echo "Nginx is already running with PID $nginx_pid. Stopping it first..."
    nginx -s stop
    sleep 1
fi

# Get the current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check the OS type and set Nginx options accordingly
if [[ "$(uname)" == "Darwin" ]]; then
    # macOS
    NGINX_OPTS="-c \"$DIR/nginx.conf\" -p \"$DIR\" -g 'daemon off;'"
    echo "Detected macOS system"
else
    # Linux and others
    NGINX_OPTS="-c \"$DIR/nginx.conf\" -p \"$DIR\" -g 'daemon off;'"
    echo "Detected Linux system"
fi

# Start nginx with the configuration
echo "Starting Nginx server at http://localhost:7001"
echo "Press Ctrl+C to stop the server"

# Run nginx in the foreground so we can catch Ctrl+C
echo "Running: nginx $NGINX_OPTS"
eval "nginx $NGINX_OPTS"

# This will only execute if nginx exits
echo "Nginx has stopped."
