#!/bin/bash

# Get the current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Stop nginx
echo "Stopping Nginx server..."
nginx -s stop -c "$DIR/nginx.conf" -p "$DIR"

# Check if nginx stopped successfully
if [ $? -eq 0 ]; then
    echo "Nginx stopped successfully."
else
    echo "Failed to stop Nginx. It might not be running."
    
    # Kill by process name if needed
    nginx_pid=$(pgrep -f "nginx: master process" || echo "")
    if [ -n "$nginx_pid" ]; then
        echo "Trying to force kill nginx with PID $nginx_pid..."
        kill -9 $nginx_pid
        echo "Nginx force killed."
    fi
fi