import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';

const SEV_COLOR = {
  nominal: 'var(--color-nominal)',
  medium: 'var(--color-sev-medium)',
  high: 'var(--color-sev-high)',
  critical: 'var(--color-sev-critical)',
  live: 'var(--color-live)',
};

function Sparkline({ data, color }) {
  if (!data || data.length < 2) return <div className="h-7" />;
  const w = 84;
  const h = 28;
  const max = Math.max(...data, 1);
  const step = w / (data.length - 1);
  const pts = data.map((v, i) => [i * step, h - (v / max) * h]);
  const line = pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const flat = Math.max(...data) === Math.min(...data);
  const area = `${line} L${w},${h} L0,${h} Z`;
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible">
      {!flat && <path d={area} fill={color} fillOpacity={0.12} />}
      <path d={line} fill="none" stroke={color} strokeWidth={1.4} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

export default function StatCard({ label, value, trend, direction, sparkline, severity, tone = 'neutral' }) {
  const color = SEV_COLOR[severity] || SEV_COLOR.nominal;
  const Arrow = direction === 'up' ? ArrowUpRight : direction === 'down' ? ArrowDownRight : Minus;
  const trendColor = trendTone(tone, direction);

  return (
    <div className="flex min-w-[140px] flex-1 flex-col justify-between rounded-lg border border-hairline bg-panel p-3">
      <div className="flex items-center justify-between">
        <span className="mono text-[10px] tracking-[0.18em] uppercase text-ghost">{label}</span>
        <span className="flex items-center gap-0.5 mono text-[11px]" style={{ color: trendColor }}>
          {trend != null ? `${direction === 'flat' ? '' : (direction === 'up' ? '+' : '−')}${trend}` : ''}
          {trend != null && <Arrow className="h-3 w-3" />}
        </span>
      </div>
      <div className="mt-1 flex items-end justify-between gap-2">
        <span className="mono text-2xl font-semibold leading-none" style={{ color }}>
          {typeof value === 'number' ? value.toLocaleString() : value ?? '—'}
        </span>
        <Sparkline data={sparkline} color={color} />
      </div>
    </div>
  );
}

// Trend badge color is semantic, never hardcoded:
//  - "negative" metrics (critical/high/medium/incidents): up = red, down = green
//  - "neutral" metrics (events/humans): cyan for any movement, gray when flat
function trendTone(tone, direction) {
  if (tone === 'negative') {
    if (direction === 'up') return 'var(--color-sev-critical)';
    if (direction === 'down') return 'var(--color-nominal)';
    return 'var(--color-ghost)';
  }
  if (direction === 'up' || direction === 'down') return 'var(--color-live)';
  return 'var(--color-ghost)';
}
