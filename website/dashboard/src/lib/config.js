// Shared backend access config.
export const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export function snapshotUrl(cameraId, incidentId, file) {
  if (!file) return null;
  return `${API_BASE}/storage/incidents/${cameraId}/${incidentId}/${file}`;
}

export function liveStreamUrl() {
  return `${API_BASE}/stream/live`;
}

export function cameraStreamUrl(camId) {
  if (!camId) return liveStreamUrl();
  return `${API_BASE}/stream/camera/${camId}`;
}

// Severity color mapping per the visual spec — reserved strictly for severity.
export const SEVERITY = {
  critical: { color: '#ef4444', label: 'Critical' },
  high: { color: '#ff8a3d', label: 'High' },
  medium: { color: '#f5a623', label: 'Medium' },
  low: { color: '#22c55e', label: 'Low' },
  informational: { color: '#4ade80', label: 'Informational' },
};

export function severityKey(label) {
  const l = String(label || '').toUpperCase();
  if (l.includes('CRIT')) return 'critical';
  if (l.includes('HIGH')) return 'high';
  if (l.includes('MED')) return 'medium';
  if (l.includes('LOW')) return 'low';
  if (l.includes('INFO')) return 'informational';
  return 'informational';
}

// Deterministic pseudo-rand for stable schematic placements.
export function hashish(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}
