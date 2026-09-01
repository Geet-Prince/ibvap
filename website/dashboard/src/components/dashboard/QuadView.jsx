/**
 * QuadView.jsx (Now a full Camera Picker)
 * Shows all available cameras in a scrollable grid.
 * Uses static snapshots that refresh periodically to prevent browser connection limits.
 */
import { useState, useEffect, useRef } from 'react';
import { snapshotUrl } from '../../lib/config';

// 1. We need to add snapshotUrl to config.js or just hardcode the path.
// The existing cameraStreamUrl is exported from '../../lib/config'.
// We can just construct the URL manually.

const REFRESH_INTERVAL_MS = 2500;

function CamTile({ cam, isActive, onClick }) {
  const [broken, setBroken] = useState(false);
  const [timestamp, setTimestamp] = useState(Date.now());

  // Periodically refresh the snapshot
  useEffect(() => {
    if (!cam.online) return;
    const interval = setInterval(() => {
      setTimestamp(Date.now());
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [cam.online]);

  // If the active camera changes, reset broken state
  useEffect(() => {
    setBroken(false);
  }, [cam.id]);

  const src = `/stream/snapshot/${cam.id}?t=${timestamp}`;

  return (
    <div
      role="button"
      tabIndex={0}
      className={`relative cursor-pointer select-none overflow-hidden rounded-md border transition-all duration-200 ${
        isActive
          ? 'border-live ring-1 ring-live/40 shadow-[0_0_8px_2px_rgba(34,211,238,0.35)]'
          : 'border-hairline hover:border-live/40'
      }`}
      style={{ aspectRatio: '16/9', background: '#000' }}
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
    >
      {broken ? (
        <div className="flex h-full w-full flex-col items-center justify-center gap-1 bg-[#070b11]">
          <span className="text-ghost/30 text-[10px] mono uppercase">Offline</span>
        </div>
      ) : (
        <img
          src={src}
          alt={cam.name || cam.id}
          className="h-full w-full object-cover"
          onError={() => setBroken(true)}
        />
      )}

      {isActive && (
        <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-live shadow-[0_0_5px_2px_rgba(34,211,238,0.7)] animate-pulse" />
      )}

      <div
        className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-1.5 py-0.5 gap-1"
        style={{ background: 'linear-gradient(transparent, rgba(0,0,0,0.75))' }}
      >
        <span className="mono text-[8px] uppercase tracking-widest text-white/80 truncate leading-tight">
          {cam.name || cam.id}
        </span>
        {cam.objects != null && (
          <span className="mono text-[8px] text-live/90 flex-shrink-0">
            {cam.objects} obj
          </span>
        )}
      </div>

      {!cam.online && !broken && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/40">
          <span className="rounded bg-black/70 px-2 py-0.5 mono text-[9px] uppercase text-sev-critical/80 tracking-wider">
            Offline
          </span>
        </div>
      )}
    </div>
  );
}

export default function QuadView({ cameras = [], activeCameraId, onSelect }) {
  // We no longer slice. We show ALL cameras.
  const visible = cameras;
  const [isOpen, setIsOpen] = useState(false);

  if (visible.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-ghost/40 text-xs mono">
        No cameras detected
      </div>
    );
  }

  const activeCam = visible.find(c => c.id === activeCameraId) || visible[0];

  return (
    <div className="flex flex-col w-full">
      {/* Dropdown Toggle Button */}
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-3 py-2 bg-[#0d131f] hover:bg-white/5 border-b border-hairline transition-colors"
      >
        <span className="text-xs mono tracking-wider text-white/80">
          Selected: <span className="text-live">{activeCam?.name || activeCam?.id || 'None'}</span>
        </span>
        <span className="text-xs text-ghost/50">{isOpen ? '▲' : '▼'}</span>
      </button>

      {/* Expandable Grid */}
      {isOpen && (
        <div className="grid grid-cols-2 gap-1.5 p-2 max-h-[400px] overflow-y-auto custom-scrollbar bg-[#0a0f18]">
          {visible.map((cam) => (
            <CamTile
              key={cam.id}
              cam={cam}
              isActive={cam.id === activeCameraId}
              onClick={() => {
                onSelect?.(cam.id);
                setIsOpen(false);
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
