// Shared severity/color + time helpers kept out of components so files stay
// component-only (fast-refresh friendly).

export const SEV_COLOR = {
  critical: 'var(--color-sev-critical)',
  high: 'var(--color-sev-high)',
  medium: 'var(--color-sev-medium)',
  low: 'var(--color-nominal)',
  nominal: 'var(--color-nominal)',
  informational: 'var(--color-live)',
};

export function relTime(iso) {
  const then = new Date(iso).getTime();
  if (!then) return '';
  const s = Math.max(0, (Date.now() - then) / 1000);
  if (s < 60) return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
}
