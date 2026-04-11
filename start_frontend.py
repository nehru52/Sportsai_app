#!/usr/bin/env python3
"""
Simple HTTP server for the SportsAI frontend.
Run this to serve the frontend on http://localhost:8080
"""
import http.server
import socketserver
import os
import sys

# Change to frontend directory
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend')

if not os.path.exists(frontend_dir):
    print(f"ERROR: Frontend directory not found at {frontend_dir}")
    sys.exit(1)

os.chdir(frontend_dir)

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()
    
    def log_message(self, format, *args):
        # Custom logging
        print(f"[{self.log_date_time_string()}] {format % args}")

print(f"""
╔════════════════════════════════════════════════════════════╗
║  SportsAI Frontend Server                                  ║
╚════════════════════════════════════════════════════════════╝

✓ Serving from: {frontend_dir}
✓ Frontend running at: http://localhost:{PORT}
✓ API should be running at: http://localhost:8001

Open your browser and go to: http://localhost:{PORT}

Press Ctrl+C to stop the server.
""")

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✓ Frontend server stopped.")

