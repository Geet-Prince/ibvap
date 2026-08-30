"""
alarm_manager/src/api.py
FastAPI server — serves REST + WebSocket alerts to the dashboard website.
Owner: Prince
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from alarm_manager.src.database import get_recent_events, init_db
from alarm_manager.src import register_subscriber, unregister_subscriber

app = FastAPI(title="IBVAP Alarm Manager API")

# Allow the website (any origin) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve snapshots as static files
_SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / "storage" / "media" / "snapshots"
_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/snapshots", StaticFiles(directory=str(_SNAPSHOT_DIR)), name="snapshots")

# Serve the website
_WEBSITE_DIR = Path(__file__).resolve().parents[2] / "website"
if _WEBSITE_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(_WEBSITE_DIR), html=True), name="website")


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/")
async def root():
    return {"status": "IBVAP Alarm Manager is running", "docs": "/docs"}


@app.get("/api/events")
async def get_events(limit: int = 50):
    """Return the most recent events from the database."""
    return JSONResponse(content=get_recent_events(limit))


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket endpoint — streams live alerts to the dashboard."""
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    register_subscriber(queue)
    try:
        while True:
            alert = await queue.get()
            await websocket.send_json(alert)
    except WebSocketDisconnect:
        pass
    finally:
        unregister_subscriber(queue)
