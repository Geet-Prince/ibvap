import { Radar } from 'lucide-react';

// Severity → color, same keys used across the alert list / stat cards.
// informational maps to green (effectively nominal threat).
const BLIP_COLOR = {
  critical: '#ef4444', // combat red
  high: '#ff8a3d',     // tactical orange
  medium: '#f5a623',   // hazard amber
  low: '#22c55e',      // tactical army green
  nominal: '#22c55e',  // tactical army green
  informational: '#4ade80', // army phosphor green
};

// Schematic radar — accepts sector-relative {x, y (0..100), severity, item} points.
// A rotating sweep arc + range rings convey "live" state. The radar fills the
// content area (large, centered) and is drawn directly on the panel surface with
// the technical grid extending across the whole panel — no inner/nested dark box.
export default function RadarMap({
  points = [],
  onSelectPoint,
  selectedId,
}) {
  return (
    <div className="flex flex-col h-full overflow-hidden rounded-lg border border-hairline bg-panel">
      <div className="flex items-center justify-between border-b border-hairline px-3 py-2">
        <span className="flex items-center gap-2">
          <Radar className="h-3.5 w-3.5 text-live" />
          <span className="mono text-[10px] tracking-[0.2em] uppercase text-ghost">Sector Coverage</span>
        </span>
        <span className="mono text-[10px] text-ghost">{points.length} blip{points.length === 1 ? '' : 's'}</span>
      </div>

      <div className="relative flex flex-1 w-full items-center justify-center">
        {/* Technical grid — spans the full panel behind the radar, tactical army olive */}
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              'linear-gradient(rgba(34,49,36,0.5) 1px, transparent 1px),' +
              'linear-gradient(90deg, rgba(34,49,36,0.5) 1px, transparent 1px)',
            backgroundSize: '28px 28px',
          }}
        />

        {/* Radar coordinate space — a compact square, centered with equal
            breathing room on all sides. Blips map onto this square (0..100%), so
            they scale with it and always stay inside the radar. */}
        <div
          className="relative aspect-square h-[250px] max-h-full w-full max-w-[250px]"
          style={{
            backgroundImage:
              'radial-gradient(circle at center, rgba(74,222,128,0.08), transparent 68%)',
          }}
        >
          {[20, 40, 60].map((r) => (
            <div
              key={r}
              className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-hairline/50"
              style={{ width: `${r * 2}%`, height: `${r * 2}%` }}
            />
          ))}
          {/* outer ring is a touch brighter to define the radar edge */}
          <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-hairline/80" style={{ width: '100%', height: '100%' }} />

          {/* crosshair */}
          <div className="pointer-events-none absolute left-1/2 top-0 h-full w-px bg-hairline/30" />
          <div className="pointer-events-none absolute left-0 top-1/2 h-px w-full bg-hairline/30" />

          {/* rotating sweep arc with tactical phosphor green glow */}
          <div
            className="pointer-events-none absolute inset-0 animate-radar-sweep"
            style={{
              transformOrigin: '50% 50%',
              borderRadius: '50%',
              boxShadow: '0 0 32px 2px rgba(74,222,128,0.12)',
              background:
                'conic-gradient(from 0deg, rgba(74,222,128,0.22), rgba(74,222,128,0.04) 30deg, transparent 60deg)',
            }}
          />

          {/* blips (clickable) */}
          {points.map((p) => {
            const color = BLIP_COLOR[p.severity] || BLIP_COLOR.nominal;
            const isSelected = selectedId === p.id;
            return (
              <button
                key={p.id ?? `${p.x}-${p.y}`}
                type="button"
                title={p.label || p.id}
                onClick={() => onSelectPoint?.(p.item)}
                className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full"
                style={{
                  left: `${p.x}%`,
                  top: `${p.y}%`,
                  width: isSelected ? 16 : 11,
                  height: isSelected ? 16 : 11,
                }}
              >
                <span
                  className="absolute inset-0 rounded-full transition-shadow"
                  style={{
                    background: color,
                    boxShadow: isSelected
                      ? `0 0 0 2px ${color}, 0 0 16px 3px ${color}99`
                      : `0 0 10px 2px ${color}77`,
                  }}
                />
              </button>
            );
          })}
        </div>
      </div>

      {/* Legend — in-panel footer, same muted small-caps style as panel chrome */}
      <div className="flex items-center justify-center gap-4 border-t border-hairline px-3 py-2">
        {[
          { label: 'Low', color: BLIP_COLOR.low },
          { label: 'Medium', color: BLIP_COLOR.medium },
          { label: 'High', color: BLIP_COLOR.high },
          { label: 'Critical', color: BLIP_COLOR.critical },
        ].map((l) => (
          <span key={l.label} className="flex items-center gap-1.5 mono text-[9px] uppercase tracking-wider text-ghost">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: l.color }} />
            {l.label}
          </span>
        ))}
      </div>
    </div>
  );
}
