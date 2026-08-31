"""
alarm_manager/src/api.py  (v2 — with MJPEG live stream + incident endpoints)
Owner: Prince
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from alarm_manager.src.database import get_recent_events, init_db, update_event_status
from alarm_manager.src.incident_store import get_all_incidents, update_status
from alarm_manager.src.frame_buffer import LIVE_FRAME
from alarm_manager.src.stats import compute_stats
from alarm_manager.src import register_subscriber, unregister_subscriber

app = FastAPI(title="IBVAP API v2")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# Static: snapshots, incidents, website
_STORAGE     = Path(__file__).resolve().parents[2] / "storage"
_WEBSITE_DIR = Path(__file__).resolve().parents[2] / "website"
_INCIDENTS   = _STORAGE / "incidents"

app.mount("/storage", StaticFiles(directory=str(_STORAGE)), name="storage")
if _WEBSITE_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(_WEBSITE_DIR), html=True), name="ui")


@app.on_event("startup")
async def _startup(): init_db()


@app.get("/")
async def root():
    return {"status": "IBVAP v2 running", "dashboard": "/ui", "docs": "/docs"}


# ── Live MJPEG Stream ───────────────────────────────────────────────────────
async def _mjpeg_gen():
    """Yield JPEG frames as multipart for the browser <img> tag."""
    while True:
        frame = LIVE_FRAME.read()
        if frame:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        await asyncio.sleep(0.04)   # ~25 fps max


@app.get("/stream/live")
async def live_stream():
    return StreamingResponse(
        _mjpeg_gen(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ── REST APIs ───────────────────────────────────────────────────────────────
@app.get("/api/events")
async def api_events(limit: int = 50):
    return JSONResponse(content=get_recent_events(limit))


@app.get("/api/incidents")
async def api_incidents(limit: int = 30):
    return JSONResponse(content=get_all_incidents(limit))


@app.get("/api/incidents/{incident_id}")
async def api_incident_detail(incident_id: str):
    meta_file = _INCIDENTS / incident_id / "incident.json"
    if not meta_file.exists():
        return JSONResponse(status_code=404, content={"error": "not found"})
    import json
    return JSONResponse(content=json.loads(meta_file.read_text()))


# ── Status updates (Escalate / Mark Reviewed) ───────────────────────────────
@app.patch("/api/alerts/{alert_id}")
async def api_update_alert(alert_id: str, body: dict):
    status = (body or {}).get("status", "").strip()
    if not status:
        return JSONResponse(status_code=400, content={"error": "status required"})
    if not update_event_status(alert_id, status):
        return JSONResponse(status_code=404, content={"error": "alert not found"})
    return {"event_id": alert_id, "status": status}


@app.patch("/api/events/{event_id}")
async def api_update_event(event_id: str, body: dict):
    status = (body or {}).get("status", "").strip()
    if not status:
        return JSONResponse(status_code=400, content={"error": "status required"})
    if not update_event_status(event_id, status):
        return JSONResponse(status_code=404, content={"error": "event not found"})
    return {"event_id": event_id, "status": status}


@app.patch("/api/incidents/{incident_id}")
async def api_update_incident(incident_id: str, body: dict):
    status = (body or {}).get("status", "").strip()
    if not status:
        return JSONResponse(status_code=400, content={"error": "status required"})
    if not update_status(incident_id, status):
        return JSONResponse(status_code=404, content={"error": "incident not found"})
    return {"incident_id": incident_id, "status": status}


# ── Aggregated stats for the dashboard ───────────────────────────────────────
@app.get("/api/stats")
async def api_stats():
    return compute_stats()


# ── Live pipeline telemetry (per-frame human count, same source as feed) ──────
@app.get("/api/live")
async def api_live():
    info = LIVE_FRAME.live()
    if not info["live"]:
        # Make a stalled pipeline visible instead of silently reporting 0.
        import logging
        logging.getLogger("ibvap.api").warning(
            "live source stale — pipeline may not be writing frames."
        )
    return info


# ── WebSocket live alerts ───────────────────────────────────────────────────
@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await websocket.accept()
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    register_subscriber(q)
    try:
        while True:
            alert = await q.get()
            await websocket.send_json(alert)
    except WebSocketDisconnect:
        pass
    finally:
        unregister_subscriber(q)
