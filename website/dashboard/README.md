# IBVAP — Border Intelligence Dashboard (React)

A redesigned live surveillance / alerts monitoring console built with **React + Vite + Tailwind CSS v4**. This is a separate frontend living alongside the existing vanilla `website/index.html` page, and it connects directly to the IBVAP FastAPI backend that runs on `http://localhost:8000`.

## Run

```bash
npm install
npm run dev
```

The Vite dev server proxies `/api`, `/storage`, `/stream`, and `/ws` to the backend on `:8000`, so start the backend first (`python start_server.py` from the repo root).

- Dev server: `http://localhost:5173`
- API docs (backend): `http://localhost:8000/docs`

## Scripts

| Command | Description |
| --- | --- |
| `npm run dev` | Start Vite dev server with backend proxy |
| `npm run build` | Production build to `dist/` |
| `npm run lint` | Oxlint |
| `npm run preview` | Preview the production build |

## Component structure

```
src/components/dashboard/
  DashboardLayout.jsx    — page shell, owns state/data flow, responsive grid
  TopBar.jsx             — brand, sector selector, live clock, connection pill
  StatStrip.jsx          — 6 metric cards
    StatCard.jsx           — single metric + trend + sparkline
  CameraPanel.jsx        — left column
    MainFeed.jsx           — MJPEG feed player + detection overlay
    CameraThumbGrid.jsx    — camera thumbnails
  MonitorPanel.jsx       — center column
    RadarMap.jsx           — schematic radar with live blips
    AlertTabs.jsx          — Alerts / Incidents switcher
    AlertList.jsx          — scrollable list (skeleton + empty state)
      AlertRow.jsx           — single row
  DetailPanel.jsx        — right column: selected item or empty state
```

Support code: `src/lib/api.js` (normalizers + REST), `src/lib/config.js`, `src/lib/theme.js`, `src/hooks/useLiveAlerts.js` (WebSocket), `src/hooks/useClock.js`.

## Data flow

- On mount, fetch initial **alerts** (`GET /api/events`), **incidents** (`GET /api/incidents`), and **stats** (derived from the two) via REST.
- Subscribe to the live alert channel (`/ws/alerts`) and **merge** incoming alerts into state (dedup by id) rather than refetching — connection state drives the top-bar pill and feed health.
- Selecting a row sets `selectedId` in `DashboardLayout`; `DetailPanel` renders from it.
- "Escalate" / "Mark reviewed" optimistically update local state and fire a best-effort `PATCH /api/alerts|incidents/:id`.

## Data contracts (real backend shapes)

The backend (FastAPI + SQLite, not yet Express/Mongo) defines these shapes, which the normalizers map into the internal item contract:

- **Live alert** (`/ws/alerts`): `incident_id, event_type, severity, danger_label, danger_score, camera_id, track_id, module, confidence, bbox[4], snapshot, humans_detected, zone_breaches, activities, timestamp`
- **Persisted event** (`GET /api/events`): `event_id, event_type, severity, camera_id, track_id, danger_score, snapshot_path, module, attributes (JSON string), status, created_at`
- **Incident** (`GET /api/incidents`): `incident_id, camera_id, started_at, last_updated, danger_score, danger_label, modules_triggered, humans_detected, snapshots[]`, etc.

`normalizeAlert` accepts both the live and persisted shapes; `normalizeIncident` maps the folder metadata.

## Visual language

- Near-black navy `#0a0e14`, panel surfaces `#0f151e`, hairline borders `#1e2733`.
- JetBrains Mono for all telemetry/timestamps; Inter for labels.
- Severity color reserved for severity: green = nominal, amber = medium, orange = high, red = critical, cyan = live/system.
- Flat surfaces, no gradients except the radar sweep; subtle glow on live indicators.
- Three-column grid collapses to a stacked layout below `900px`, prioritizing the alert list and detail panel over the camera grid on small screens.
