#!/bin/bash

# Move to the correct directory
cd /Users/jpnunez/aicompetency/svelte_flask/

# Create directory if needed
mkdir -p backend/static

# Copy the embed.js file to the backend's static folder
cp frontend/embed/embed.js backend/static/

echo "Copied embed.js to backend/static/"