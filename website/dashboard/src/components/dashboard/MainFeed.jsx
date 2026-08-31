import { useState } from 'react';
import { VideoOff } from 'lucide-react';
import { useClock } from '../../hooks/useClock';
import { liveStreamUrl } from '../../lib/config';

const BOX_COLOR = {
  critical: '#ef4444',
  high: '#ff8a3d',
  medium: '#f5a623',
  low: '#2ecc71',
  nominal: '#2ecc71',
};

// Detection box contract: { x, y, w, h, label, confidence } in frame pixels.
export default function MainFeed({ cameraId, streamSrc, detections = [], cameraName, offline = false, humans }) {
  const [dims, setDims] = useState(null); // { nw, nh } natural stream resolution
  const [streamBroken, setStreamBroken] = useState(false); // img error → stream dead
  const now = useClock(1000);
  const time = now.toLocaleTimeString('en-GB', { hour12: false });

  const src = streamSrc ?? liveStreamUrl();
  // Container ratio tracks the ACTUAL stream resolution so there are no black
  // bars (fallback 4:3 while the first frame loads).
  const ratio = dims ? `${dims.nw} / ${dims.nh}` : '4 / 3';

  // Live per-frame human count from the pipeline. null/undefined = source
  // unknown → render "--", never a silent 0.
  const humansCount = humans != null ? humans : null;

  // Stream is "down" if the feed explicitly reports offline OR the <img> itself
  // errored (e.g. the MJPEG connection was severed when the backend died).
  const down = offline || streamBroken;

  return (
    <div className="flex flex-col overflow-hidden rounded-lg border border-hairline bg-panel">
      <div className="flex items-center justify-between border-b border-hairline px-3 py-2">
        <span className="mono text-[10px] tracking-[0.2em] uppercase text-ghost">Live Feed</span>
        <span className="flex items-center gap-2">
          <span className="mono text-[10px] uppercase tracking-wider text-ghost">{cameraName || cameraId}</span>
          <span className="flex items-center gap-1.5">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                offline ? 'bg-sev-critical' : 'bg-nominal shadow-[0_0_5px_1px_rgba(46,204,113,0.6)] animate-pulse'
              }`}
            />
            <span className="mono text-[10px] text-ghost">{time}</span>
          </span>
        </span>
      </div>

      <div
        className="relative w-full overflow-hidden bg-black"
        style={{ aspectRatio: ratio }}
      >
        {down ? (
          <div className="flex h-full w-full items-center justify-center bg-[#070b11]">
            <VideoOff className="h-8 w-8 text-ghost/40" />
          </div>
        ) : (
          <img
            key={cameraId}
            src={src}
            alt="live"
            className="h-full w-full object-cover"
            onLoad={(e) => {
              const el = e.currentTarget;
              setStreamBroken(false);
              setDims({ nw: Math.max(el.naturalWidth, 1), nh: Math.max(el.naturalHeight, 1) });
            }}
            onError={() => setStreamBroken(true)}
          />
        )}

        {/* HTML/CSS HUD overlay — replaces the debug text formerly burned
            into the streamed frame, so it stays crisp & on-theme. */}
        <div className="pointer-events-none absolute left-1.5 top-1.5 flex flex-col gap-1">
          <span className="rounded-sm bg-black/55 px-1.5 py-0.5 mono text-[9px] tracking-[0.15em] text-live">
            ● {down ? 'OFFLINE' : 'REC'}
          </span>
          <span className="w-max rounded-sm bg-black/55 px-1.5 py-0.5 mono text-[9px] tracking-[0.15em] text-fg/80">
            LIVE HUMANS: {humansCount != null ? humansCount : '--'}
          </span>
        </div>

        {/* Detection overlay */}
        {dims &&
          !down &&
          detections.length > 0 &&
          detections.map((d, i) => (
            <div
              key={i}
              className="absolute border"
              style={{
                left: `${((d.x / dims.nw) * 100).toFixed(2)}%`,
                top: `${((d.y / dims.nh) * 100).toFixed(2)}%`,
                width: `${((d.w / dims.nw) * 100).toFixed(2)}%`,
                height: `${((d.h / dims.nh) * 100).toFixed(2)}%`,
                borderColor: BOX_COLOR[d.severity] || BOX_COLOR.nominal,
              }}
            >
              <span
                className="absolute -top-0.5 left-0 -translate-y-full whitespace-nowrap rounded-sm px-1 mono text-[9px] uppercase tracking-wider"
                style={{ background: BOX_COLOR[d.severity] || BOX_COLOR.nominal, color: '#08100f' }}
              >
                {d.label}
                {d.confidence != null ? ` ${Math.round(d.confidence * 100)}%` : ''}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}
