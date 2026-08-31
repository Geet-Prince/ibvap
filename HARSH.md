# IBVAP — Border Intelligence Platform

**One simple explanation of the whole system: what it is, how the parts connect, how you start it, and what is (and isn't) working right now.**

Repository root: `D:\Projects\SIH2026\ibvap`

---

## 1. What this is (30-second summary)

IBVAP is a **border-surveillance / threat-alerting system**. A **camera** feed is analyzed live by AI modules (human detection, tracking, suspicious activity). When something suspicious is found, the system:

1. logs the event,
2. saves snapshots/incidents to disk,
3. pushes a **live alert** over a WebSocket,
4. and shows everything on a **dashboard**.

There are **two separate frontends** and one backend:

| Piece | What it is | Where |
| --- | --- | --- |
| Backend | FastAPI (Python) server — REST APIs, WebSocket, MJPEG camera stream, incident storage | `alarm_manager/` |
| Old frontend | Plain HTML/JS dashboard (one file) | `website/index.html` → `/ui` |
| **New frontend** | **React dashboard** (the redesigned one) | `website/dashboard/` → port 5173 |

---

## 2. How the pieces talk to each other (the flow)

```
        ┌──────────────────────────────────────────────────┐
        │               BACKEND  (FastAPI, :8000)          │
        │                                                  │
  Camera │                                                │  serves:
  feed ──► camera pipeline ──► LIVE_FRAME ─────────────────┼─► /stream/live   (MJPEG video)
  (run_ibvap.py)      │                                    │
        │             └─► AlarmManager ────────────────────┼─► /api/events     (alerts)
        │                              │                   │► /api/incidents  (incidents)
        │                              └─► WebSocket  ─────┼─► /ws/alerts      (live alerts)
        │                                    │             │► /storage/...    (snapshots)
        └────────────────────────────────────┼─────────────┘
                                             │  live push (merge, no refetch)
                                             ▼
                                 ┌──────────────────────────┐
                                 │   REACT DASHBOARD (:5173) │
                                 │  TopBar / Stats / Camera  │
                                 │  / Radar / Alerts / Detail│
                                 └──────────────────────────┘
```

**The key idea:** the React dashboard is **stateless re: the source of truth**. It loads initial data from the REST API once, then just **merges** live alerts from the WebSocket instead of refreshing everything.

---

## 3. How to start it (the ONLY correct way)

> ⚠️ **RULE: Never run `start_server.py` and `run_ibvap.py` at the same time.**
> `run_ibvap.py` ALREADY starts the server (port 8000) *and* the camera in one process.
> Running `start_server.py` too causes a port-8000 conflict (`Errno 10048`) and a **blank camera feed**.

### Step 1 — Fix the OMP crash (do this once, permanently)

The process crashes with `OMP: Error #15: libiomp5md.dll already initialized` because your Anaconda environment loads two copies of the OpenMP runtime together. Fix it by setting a **permanent** environment variable:

**In your PowerShell (run once):**
```
[Environment]::SetEnvironmentVariable("KMP_DUPLICATE_LIB_OK", "TRUE", "User")
```

Then **open a NEW terminal** so it picks it up.

*(If you skip this, it crashes every time, even with nothing else running.)*

### Step 2 — Start backend + camera (one terminal)

```
cd D:\Projects\SIH2026\ibvap
python run_ibvap.py
```
- Starts the API server on **:8000**
- Opens your **camera**
- A video window appears — press `q` in it to stop.

### Step 3 — Start the React dashboard (second terminal)

```
cd D:\Projects\SIH2026\ibvap\website\dashboard
npm install        # only the very first time
npm run dev
```
Open **http://localhost:5173** in your browser.

---

## 4. What is WORKING right now ✅

- **React dashboard** (the redesigned UI) — fully built:
  - TopBar (brand, sector selector, live clock, connection pill)
  - StatStrip — 6 metric cards (Events, Humans, Medium, High, Critical, Incidents) with sparklines
  - CameraPanel → Live Feed (MJPEG + detection overlay + HTML HUD overlay) + camera thumbnails
  - **Streamed feed is clean** — debug text is no longer burned into the frame; the pipeline draws it only on the local OpenCV preview, and the dashboard renders a styled HTML HUD/counts overlay instead
  - **Feed sizing fixed** — the image uses `object-fit: cover` and the container's aspect-ratio tracks the real stream resolution (no black bars / small off-center frame)
  - MonitorPanel → Radar map + Alerts/Incidents tabs + bounded-height scrollable list
  - **List visibility fixed** — the radar was `aspect-square` at full column width (huge) and the list had no max height on desktop, pushing 2000+ rows below the fold. Radar now capped (`max-w-[320px]`, centered) and the list bounded to `max-h-[460px]` + `overflow-y-auto`, so both are always visible in the column.
  - **Severity confirmed genuine** — every one of the 2008 events is `severity=informational` / `danger_score=20` and all 2007 incidents are `danger_label=LOW` (SQLite + incident.json verified). The high/medium/critical rules in `rules.yaml` have simply never matched this data; the UI coloring is read correctly, not defaulting due to a bug.
  - DetailPanel (empty state + Escalate / Mark Reviewed)
  - **Detail selection fixed** — list rows were passing the whole item object as `selectedId` (`onSelect(item)`), so `selectedItem` never matched and DetailPanel always showed the empty state. Rows now pass `item._id`, sharing the same `selectedId`/`selectedItem` state as radar blips. Clicking a row or blip populates the full detail view (snapshot, severity, location, camera, timestamp, confidence, status).
  - **Escalate / Mark Reviewed wired to real PATCH** — added backend `PATCH /api/alerts/{id}`, `PATCH /api/events/{id}`, and `PATCH /api/incidents/{id}` (persist to SQLite `events.status` and `incident.json.status`). Helper `update_event_status` in database.py and `update_status` in incident_store.py. Frontend uses `api.updateStatus()`, updates the list row optimistically, and re-fetches `/api/stats` on success so counts refresh without a page reload. Verified end-to-end on a temp server.
  - **Live human count unified + distinct from stat card** — the overlay HUD and the HUMANS stat card were reading DIFFERENT sources (overlay = last WS alert / detection count; stat = persisted peak across incidents), which is why the overlay sat at 0. Now the camera loop publishes its real per-frame count via `LIVE_FRAME.set_live()` (current frame only, never a stale previous frame), the dashboard reads it through the new `GET /api/live` endpoint and renders `LIVE HUMANS: N` (`--` when the source is stale, never a silent 0). Per-frame raw confidence is logged each 15th frame for threshold checks (`confidence_threshold: 0.50` on class 0). The stat card is relabeled **"Humans Peak"** (session aggregate) to distinguish from the live feed count.
  - **Disconnect handling — panels stay populated** — `useLiveAlerts`' `onclose`/`onerror` only set a `status` flag; it never clears alerts/incidents/stats/cameras (all live in `DashboardLayout` local state, untouched on disconnect). So when the backend/socket drops, the dashboard keeps showing the last-fetched data. A muted/gray **"Offline"** pill (reused LIVE pill styling) plus a full-width banner (**"Reconnecting…"** / **"Offline — showing last known data"**) appear under the TopBar. The feed keeps the last frame mounted with a grayscale **"NO SIGNAL"** overlay instead of unmounting to a blank box.
  - **Reconnect resync** — does NOT assume the socket replays what happened offline. `refreshAll()` re-runs the same initial REST endpoints (`/api/events`, `/api/incidents`, `/api/stats`) whenever the socket transitions back to `'live'` after being down, so missed data is caught up without a manual refresh.
  - **Dashboard no longer goes blank when backend/camera stops** — alerts, incidents, and stats are now cached to `localStorage` (`ibvap.alerts` / `ibvap.incidents` / `ibvap.stats`) on every successful fetch and status change, and hydrated on load. So even if the dashboard reloads (or a fresh tab opens) while the backend is dead, it shows the last known data instead of starting empty/blank. The stat strip shows cached numbers immediately (skeleton only when genuinely empty). The live feed also falls back to **"NO SIGNAL"** the moment the MJPEG `<img>` errors (`streamBroken`), not only when the socket reports offline.
  - **Build passes** — `npm run build` and `npm run lint` are both clean.
  - **Manual disconnect/restart test** — 1) run dashboard + `run_ibvap.py`; 2) Ctrl-C the Python process; confirm alerts/incidents/stats/camera thumbnails STAY visible (stale), the top pill shows gray "Offline", the banner shows "Offline — showing last known data", and the feed shows "NO SIGNAL" on the grayscale last frame. 3) Restart `run_ibvap.py`; confirm the pill flips back to "Live", the banner disappears, and data resyncs automatically with NO manual page refresh.
- **REST wiring** — dashboard fetches `/api/events` and `/api/incidents` on load and shows real data.
- **WebSocket wiring** — dashboard subscribes to `/ws/alerts` and merges live alerts; connection pill shows live/offline.
- **The old vanilla dashboard** at `website/index.html` (served at `http://localhost:8000/ui`) still works untouched.

---

## 5. What is NOT working / known issues ❌

| Issue | Symptom | Why / State |
| --- | --- | --- |
| **Camera feed blank / process exits** | "OMP: Error #15" crash, or port-8000 conflict | 1) Need `KMP_DUPLICATE_LIB_OK=TRUE` (fix above). 2) Don't run `start_server.py` + `run_ibvap.py` together. |
| **Port 8000 conflict (`Errno 10048`)** | Server won't bind | Another server is already on 8000. Free it, then run only `run_ibvap.py`. |
| **Live feed only works when the camera pipeline runs** | Dashboard loads but camera panel empty | `/stream/live` shows video ONLY while `run_ibvap.py` is running. No pipeline = empty feed. |
| **No PATCH endpoint on backend** | "Escalate / Mark Reviewed" only update the UI locally | The real backend has no `PATCH /api/alerts|incidents/:id`, so status changes are optimistic/local and don't persist to the DB yet. |
| **Sector selector is cosmetic** | Switching sector doesn't filter data | Backend has no per-sector channels; a placeholder `sector-a` is used. |
| **Camera thumbnails: non-live cams are placeholders** | Some thumbs show a static icon | Backend only exposes one live stream (CAM_LIVE / `/stream/live`); other camera ids are schematic. |
| **Radar map is schematic** | Blips are placed deterministically, not on real geo-coords | Backend has no lat/lng; UI uses relative positions. |
| **Live detection-overlay boxes** | Overlay shows boxes only when live alerts carry `bbox` | REST `/api/events` rows (SQLite) have no bbox; live WS alerts do. |
| **Stats trend + sparkline are derived/approximate** | Trends aren't real change-over-time yet | No dedicated stats endpoint; values computed from the two fetch endpoints. |

---

## 6. The two data shapes you'll care about (backend contracts)

**Live alert (WebSocket `/ws/alerts`)**
```
incident_id, event_type, severity, danger_label, danger_score,
camera_id, track_id, module, confidence, bbox[4], snapshot,
humans_detected, zone_breaches, activities, timestamp
```

**Persisted event (`GET /api/events`) — DIFFERENT shape**
```
event_id, event_type, severity, camera_id, track_id, danger_score,
snapshot_path, module, attributes (JSON string), status, created_at
```

> ⚠️ These two are **not the same shape**. The dashboard handles both: `src/lib/api.js → normalizeAlert()` detects which shape it got and normalizes both. This was a real gotcha found while wiring it up.

**Incident (`GET /api/incidents`)**
```
incident_id, camera_id, started_at, last_updated, danger_score,
danger_label, modules_triggered, humans_detected, snapshots[], ...
```

---

## 7. The new frontend — where everything lives

```
website/dashboard/
  src/
    App.jsx → renders DashboardLayout
    index.css  (Tailwind theme: colors, fonts, severity palette)
    lib/
      api.js      — REST calls + normalizers (events/incidents/stats)
      config.js   — API base URL, severity colors, snapshot URLs
      theme.js    — shared severity colors + relative-time helper
    hooks/
      useLiveAlerts.js  — WebSocket subscribe + merge
      useClock.js       — live clock
    components/dashboard/
      DashboardLayout.jsx   — page shell + state/data flow + grid
      TopBar.jsx
      StatStrip.jsx / StatCard.jsx
      CameraPanel.jsx / MainFeed.jsx / CameraThumbGrid.jsx
      MonitorPanel.jsx / RadarMap.jsx / AlertTabs.jsx / AlertList.jsx / AlertRow.jsx
      DetailPanel.jsx
```

### Data flow inside the dashboard
1. **On mount:** fetch alerts (`GET /api/events`), incidents (`GET /api/incidents`), and derived stats.
2. **Live:** `useLiveAlerts` connects to `/ws/alerts`, merges new alerts (dedup by id), updates connection status.
3. **Select a row** → sets `selectedId` → `DetailPanel` renders that item.
4. **Escalate / Mark Reviewed** → optimistic local update + best-effort `PATCH` (currently the endpoint doesn't exist).

### Design (from the build spec)
- Dark tactical theme: near-black navy `#0a0e14`, panels `#0f151e`, hairline borders `#1e2733`.
- JetBrains Mono for telemetry, Inter for labels.
- Severity colors reserved strictly: green=nominal, amber=medium, orange=high, red=critical, cyan=live/system.
- Flat surfaces, no gradients except the radar sweep; subtle glows on "live" indicators.

---

## 8. Quick reference — useful commands

| Task | Command |
| --- | --- |
| Fix OMP crash (once) | `[Environment]::SetEnvironmentVariable("KMP_DUPLICATE_LIB_OK","TRUE","User")` |
| Start backend + camera | `python run_ibvap.py` (in `D:\Projects\SIH2026\ibvap`) |
| Start React dashboard | `cd website/dashboard && npm run dev` |
| Old dashboard URL | `http://localhost:8000/ui` |
| React dashboard URL | `http://localhost:5173` |
| API docs | `http://localhost:8000/docs` |
| Check who's on port 8000 | `netstat -ano | findstr :8000` |
| Free a busy port | `taskkill /PID <pid> /F` |
| React build (prod) | `cd website/dashboard && npm run build` |
| React lint | `cd website/dashboard && npm run lint` |

---

## 9. Common errors & fixes

**`Errno 10048` (port 8000 busy)**
→ Stop other IBVAP servers. Run ONLY `run_ibvap.py`. Never also run `start_server.py`.

**`OMP: Error #15` crash**
→ Set `KMP_DUPLICATE_LIB_OK=TRUE` permanently (see Step 1) and open a new terminal.

**Dashboard loads but camera panel is black**
→ `run_ibvap.py` must be running (that's what feeds `/stream/live`).  
→ Make sure no OTHER process is serving port 8000.

**Alerts list empty**
→ Backend not running, or WebSocket not connected (top-right pill shows "Offline").
