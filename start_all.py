#!/usr/bin/env python3
"""
Start both frontend and backend servers for SportsAI.
"""
import subprocess
import sys
import os
import time

def start_servers():
    print("""
╔════════════════════════════════════════════════════════════╗
║  SportsAI - Starting All Servers                          ║
╚════════════════════════════════════════════════════════════╝
""")
    
    # Start backend API
    print("🚀 Starting Backend API on port 8001...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8001"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    time.sleep(2)  # Give backend time to start
    
    # Start frontend server
    print("🚀 Starting Frontend on port 8080...")
    frontend = subprocess.Popen(
        [sys.executable, "start_frontend.py"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    print("""
✅ All servers started!

📊 Backend API:  http://localhost:8001/docs
🎨 Frontend:     http://localhost:8080

Open your browser to: http://localhost:8080

Press Ctrl+C to stop all servers.
""")
    
    try:
        # Keep running until Ctrl+C
        backend.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all servers...")
        backend.terminate()
        frontend.terminate()
        backend.wait()
        frontend.wait()
        print("✅ All servers stopped.")

if __name__ == "__main__":
    start_servers()
