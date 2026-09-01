/**
 * QuadView.jsx  —  Camera picker with live MJPEG thumbnails
 *
 * Layout:
 *   - Shows up to 4 camera tiles in a 2×2 grid.
 *   - Each tile streams raw MJPEG from /stream/camera/<id>.
 *   - Clicking a tile → selects that camera to the big main feed.
 *   - Auto-rotates the highlighted tile every ROTATE_SEC seconds.
 *   - Active tile glows cyan; camera name & object count shown as HUD.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { cameraStreamUrl } from '../../lib/config';

const ROTATE_SEC = 8;

/** Single camera thumbnail tile */
function CamTile({ cam, isActive, onClick }) {
  const [broken, setBroken] = useState(false);
  // Unique key forces img remount so browser reconnects the MJPEG stream
  const [streamKey, setStreamKey] = useState(0);

  useEffect(() => {
    setBroken(false);
    setStreamKey(k => k + 1);
  }, [cam.id]);

  const src = cameraStreamUrl(cam.id);

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
      {/* MJPEG stream thumbnail */}
      {broken ? (
        <div className="flex h-full w-full flex-col items-center justify-center gap-1 bg-[#070b11]">
          <span className="text-ghost/30 text-[10px] mono uppercase">Offline</span>
        </div>
      ) : (
        <img
          key={`${cam.id}-${streamKey}`}
          src={src}
          alt={cam.name || cam.id}
          className="h-full w-full object-cover"
          onError={() => setBroken(true)}
        />
      )}

      {/* Active indicator dot */}
      {isActive && (
        <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-live shadow-[0_0_5px_2px_rgba(34,211,238,0.7)] animate-pulse" />
      )}

      {/* Bottom HUD bar */}
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

      {/* Offline pill overlay */}
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

/** 2×2 grid of camera tiles */
export default function QuadView({ cameras = [], activeCameraId, onSelect }) {
  const visible = cameras.slice(0, 4);

  // Which tile is auto-highlighted
  const [hlIdx, setHlIdx] = useState(0);
  const timerRef = useRef(null);

  const startTimer = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setHlIdx(prev => (visible.length > 0 ? (prev + 1) % visible.length : 0));
    }, ROTATE_SEC * 1000);
  }, [visible.length]);

  useEffect(() => {
    if (visible.length === 0) return;
    startTimer();
    return () => clearInterval(timerRef.current);
  }, [visible.length, startTimer]);

  const handleSelect = (idx, camId) => {
    setHlIdx(idx);
    startTimer();         // reset auto-rotate countdown
    onSelect?.(camId);
  };

  if (visible.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-ghost/40 text-xs mono">
        No cameras detected
      </div>
    );
  }

  // Determine which idx matches the externally active camera
  const externalIdx = visible.findIndex(c => c.id === activeCameraId);

  return (
    <div className="grid grid-cols-2 gap-1.5 p-2">
      {visible.map((cam, idx) => (
        <CamTile
          key={cam.id}
          cam={cam}
          isActive={idx === hlIdx || idx === externalIdx}
          onClick={() => handleSelect(idx, cam.id)}
        />
      ))}
    </div>
  );
}
