#!/usr/bin/env python3
"""
Simple HTTP Server for Sapientum AI Embed

This script starts a simple HTTP server with CORS support for the Sapientum AI embed files.
Use this if you don't have Nginx installed or prefer a simpler solution.
"""

import http.server
import socketserver
import os

PORT = 7000

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept')
        self.send_header('Access-Control-Max-Age', '1728000')
        self.end_headers()

def main():
    # Change directory to the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"Starting Sapientum AI Embed server on port {PORT}...")
    print(f"Access the server at: http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server")
    
    Handler = CORSHTTPRequestHandler
    httpd = socketserver.TCPServer(("", PORT), Handler)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()
    
if __name__ == "__main__":
    main()