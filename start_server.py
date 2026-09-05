"""
start_server.py — Starts the IBVAP Alarm Manager API + Dashboard

Usage:
    python start_server.py
    Then open: http://localhost:8000/ui
"""
import sys
import subprocess

try:
    import multipart
except ImportError:
    print("Auto-installing python-multipart into your environment...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-multipart"])

import uvicorn
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from alarm_manager.src.api import app as api_app

if __name__ == "__main__":
    print("=" * 55)
    print("  IBVAP Alarm Manager Server")
    print("  API Docs:  http://localhost:8000/docs")
    print("  Dashboard: http://localhost:8000/ui")
    print("=" * 55)
    uvicorn.run(
        api_app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="warning",
    )
