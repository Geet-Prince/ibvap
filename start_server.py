"""
start_server.py — Starts the IBVAP Alarm Manager API + Dashboard

Usage:
    python start_server.py
    Then open: http://localhost:8000/ui
"""
import sys
import uvicorn
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    print("=" * 55)
    print("  IBVAP Alarm Manager Server")
    print("  API Docs:  http://localhost:8000/docs")
    print("  Dashboard: http://localhost:8000/ui")
    print("=" * 55)
    uvicorn.run(
        "alarm_manager.src.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="warning",
    )
