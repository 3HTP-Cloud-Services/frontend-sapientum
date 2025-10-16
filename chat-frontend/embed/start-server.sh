#!/bin/bash

# Get the current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Sapientum AI Embed Server"
echo "========================="
echo

# Check if nginx is installed
if command -v nginx &> /dev/null; then
    echo "Nginx is installed. Will use Nginx server."
    echo
    # Try to use nginx
    "$DIR/start-nginx.sh"
else
    echo "Nginx is not installed. Will use Python server instead."
    echo
    # Use the Python server as a fallback
    "$DIR/start-python-server.sh"
fi