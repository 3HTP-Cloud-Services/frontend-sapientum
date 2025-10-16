# Sapientum AI Embed Server

This directory contains the files needed to run a simple HTTP server for serving the Sapientum AI embed examples and scripts.

## Files

- `embed.js` - The embed script used to embed Sapientum AI
- `index.html` - Main page with links to examples
- `embed-example.html` - Basic example for embedding
- `embed-test.html` - Test suite for the embed functionality
- `external-test.html` - Example of embedding in a third-party site
- `EMBED_README.md` - Documentation for the embed functionality
- `mime.types` - MIME types for Nginx
- `nginx.conf` - Nginx configuration file
- `server.py` - Python alternative HTTP server

## Quick Start

The easiest way to run the server is to use the `start-server.sh` script, which will automatically choose between Nginx and Python:

```bash
./start-server.sh
```

The server will run on port 7000. You can access it at:

http://localhost:7000

## Running the Server Manually

### Option 1: Nginx Server

If you have Nginx installed, you can run:

```bash
./start-nginx.sh
```

### Option 2: Python Server

If you prefer to use Python (or don't have Nginx installed):

```bash
./start-python-server.sh
```

## Testing the Embed

1. Make sure your Sapientum server is running (typically on port 5173 for development)
2. Start the embed server as described above
3. Navigate to http://localhost:7000 in your browser
4. Click on "Basic Example" to see the basic embed example
5. Click "Load Embed" to load the Sapientum AI application in the embed

## Stopping the Server

- If you're using the foreground server (start-nginx.sh or start-python-server.sh): Press Ctrl+C
- If you've started Nginx as a background process: `./stop-nginx.sh`

## Installation

If you need to install Nginx or set up the environment, please refer to the `INSTALL.md` file for detailed instructions.

## Important Notes

- The embed script assumes your Sapientum server is running at `http://localhost:5173`. Update this in the examples if your server is at a different location.
- CORS is enabled to allow the embed to communicate with the Sapientum server.
- If you make changes to the embed script, you might need to clear your browser cache to see the changes.
- The Python server is intended as a simple alternative and may not have all the features of Nginx.