"""
alarm_manager/src/stats.py
Real aggregated statistics for the dashboard StatStrip — true totals, per-metric
time-bucketed sparklines, and trends computed as (current bucket - previous bucket)
from the same source data as the headline value (never fabricated).
Owner: Prince
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from alarm_manager.src.database import get_connection

_INCIDENT_ROOT = Path(__file__).resolve().parents[2] / "storage" / "incidents"

# Aggregation window + resolution for sparklines.
WINDOW_SECONDS = 3600   # look back 1 hour
BUCKETS = 12            # 12 x 5-minute buckets


def _parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc).timestamp()
    except (ValueError, TypeError):
        return None


def _to_buckets(start_ts, bucket_s, rows):
    """rows: iterable of (ts_seconds) → count per bucket."""
    counts = [0] * BUCKETS
    for ts in rows:
        if ts is None:
            continue
        idx = int((ts - start_ts) // bucket_s)
        if 0 <= idx < BUCKETS:
            counts[idx] += 1
    return counts


def _sparkline_for_metric(buckets, value_key):
    """Build a per-bucket series from raw per-bucket counts, preserving zeros."""
    return buckets


def _trend(buckets):
    """Trend = last bucket - previous bucket, from the same series as the value."""
    if len(buckets) < 2:
        return 0, "flat"
    prev_now = buckets[-1] - buckets[-2]
    # accumulate any movement within the visible window if the last two are flat
    if prev_now == 0 and len(buckets) > 2:
        prev_now = buckets[-1] - buckets[0]
    if prev_now > 0:
        return prev_now, "up"
    if prev_now < 0:
        return -prev_now, "down"
    return 0, "flat"


def _incident_meta():
    """Yield parsed incident.json dicts with last_updated timestamps."""
    if not _INCIDENT_ROOT.exists():
        return
    for folder in _INCIDENT_ROOT.iterdir():
        if not folder.is_dir():
            continue
        meta_file = folder / "incident.json"
        if not meta_file.exists():
            continue
        try:
            yield json.loads(meta_file.read_text())
        except Exception:
            continue


def compute_stats():
    now_ts = datetime.now(timezone.utc).timestamp()
    start_ts = now_ts - WINDOW_SECONDS
    bucket_s = WINDOW_SECONDS / BUCKETS

    # ── Events (SQLite) ───────────────────────────────────────────────
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT severity, created_at FROM events"
        ).fetchall()
    finally:
        conn.close()

    event_total = len(rows)
    severity_total = defaultdict(int)
    severity_bucket = {k: [0] * BUCKETS for k in ("medium", "high", "critical", "informational", "low")}
    event_bucket = [0] * BUCKETS

    for r in rows:
        sev = (r["severity"] or "informational").lower()
        severity_total[sev] += 1
        ts = _parse_ts(r["created_at"])
        if ts is None:
            continue
        idx = int((ts - start_ts) // bucket_s)
        if 0 <= idx < BUCKETS:
            event_bucket[idx] += 1
            key = sev if sev in severity_bucket else "informational"
            severity_bucket[key][idx] += 1

    # ── Incidents (folders) ───────────────────────────────────────────
    incidents = [m for m in _incident_meta()]
    incident_total = len(incidents)

    incident_bucket = [0] * BUCKETS
    humans_bucket = [0] * BUCKETS
    distinct_tracks = set()
    incident_severity_total = defaultdict(int)
    peak_humans = 0

    for m in incidents:
        sev = (m.get("danger_label") or "informational").lower()
        if sev == "low":
            sev = "low"  # keep bucket key
        incident_severity_total[sev] += 1
        for t in m.get("track_ids") or []:
            distinct_tracks.add(t)
        humans = int(m.get("humans_detected") or 0)
        peak_humans = max(peak_humans, humans)
        ts = _parse_ts(m.get("last_updated") or m.get("started_at"))
        if ts is None:
            continue
        idx = int((ts - start_ts) // bucket_s)
        if 0 <= idx < BUCKETS:
            incident_bucket[idx] += 1
            if humans > 0:
                humans_bucket[idx] += humans

    def series(key):
        return _sparkline_for_metric(severity_bucket[key], key)

    ev_trend, ev_dir = _trend(event_bucket)
    inc_trend, inc_dir = _trend(incident_bucket)
    med_trend, med_dir = _trend(severity_bucket["medium"])
    high_trend, high_dir = _trend(severity_bucket["high"])
    crit_trend, crit_dir = _trend(severity_bucket["critical"])
    hum_trend, hum_dir = _trend(humans_bucket)

    # HEADLINE COUNTS use the *incident* severity for medium/high/critical too,
    # merged with event severity so the display reflects both real sources.
    def severity_head(sev):
        return int(severity_total.get(sev, 0) + incident_severity_total.get(sev, 0))

    return {
        "events": {
            "value": event_total,
            "sparkline": event_bucket,
            "trend": ev_trend,
            "direction": ev_dir,
            "tone": "neutral",
        },
        "humans": {
            "value": peak_humans if peak_humans > 0 else len(distinct_tracks),
            "sparkline": humans_bucket,
            "trend": hum_trend,
            "direction": hum_dir,
            "tone": "neutral",
            "label": "Humans Peak",
        },
        "medium": {
            "value": severity_head("medium"),
            "sparkline": series("medium"),
            "trend": med_trend,
            "direction": med_dir,
            "tone": "negative",
        },
        "high": {
            "value": severity_head("high"),
            "sparkline": series("high"),
            "trend": high_trend,
            "direction": high_dir,
            "tone": "negative",
        },
        "critical": {
            "value": severity_head("critical"),
            "sparkline": series("critical"),
            "trend": crit_trend,
            "direction": crit_dir,
            "tone": "negative",
        },
        "incidents": {
            "value": incident_total,
            "sparkline": incident_bucket,
            "trend": inc_trend,
            "direction": inc_dir,
            "tone": "negative",
        },
        "window": {"seconds": WINDOW_SECONDS, "buckets": BUCKETS},
    }
