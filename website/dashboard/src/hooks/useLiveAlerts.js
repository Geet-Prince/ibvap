import { useEffect, useRef, useState } from 'react';
import { API_BASE } from '../lib/config';
import { normalizeAlert } from '../lib/api';

const LS_KEY = 'ibvap.alerts';

function loadCached() {
  try {
    const raw = JSON.parse(localStorage.getItem(LS_KEY));
    return Array.isArray(raw) ? raw : [];
  } catch { return []; }
}
function saveCached(alerts) {
  try { localStorage.setItem(LS_KEY, JSON.stringify(alerts)); } catch { /* ignore */ }
}

// Subscribes to the backend alert WebSocket, merges live alerts into state,
// and reports connection status. Returns { alerts, status, reconcile }.
// Last-known alerts are cached to localStorage so that if the backend is down
// at load time the dashboard still shows stale-but-visible data (never blank).
export function useLiveAlerts({ sector } = {}) {
  const [alerts, setAlerts] = useState(loadCached);
  const [status, setStatus] = useState('connecting');
  const wsRef = useRef(null);
  const alertsRef = useRef([]);

  const push = (items) => {
    // Merge newest-first, dedup by _id so socket confirmations reconcile
    // with anything optimistically applied.
    const map = new Map();
    if (items) [...items, ...alertsRef.current].forEach((a) => map.set(a._id, a));
    else alertsRef.current.forEach((a) => map.set(a._id, a));
    alertsRef.current = Array.from(map.values()).sort(
      (a, b) => new Date(b.timestamp) - new Date(a.timestamp),
    );
    setAlerts(alertsRef.current);
    saveCached(alertsRef.current);
  };

  useEffect(() => {
    let disposed = false;
    let retry = null;

    const connect = () => {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(`${proto}://${window.location.host}${API_BASE}/ws/alerts`);
      wsRef.current = ws;

      ws.onopen = () => { if (!disposed) setStatus('live'); };
      ws.onmessage = (e) => {
        try {
          const raw = JSON.parse(e.data);
          const alert = normalizeAlert(raw);
          push([alert]);
        } catch { /* ignore malformed frames */ }
      };
      ws.onerror = () => { if (!disposed) setStatus('error'); };
      ws.onclose = () => {
        if (disposed) return;
        setStatus('offline');
        retry = setTimeout(connect, 3000);
      };
    };

    connect();
    return () => {
      disposed = true;
      if (retry) clearTimeout(retry);
      wsRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sector]);

  return { alerts, status, push };
}
