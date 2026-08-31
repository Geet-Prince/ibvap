import { useState } from 'react';
import { VideoOff } from 'lucide-react';
import { liveStreamUrl } from '../../lib/config';

// Secondary thumbnail strip. Only the live backend stream (`CAM_LIVE`) has a
// real MJPEG source — other detected camera ids render a schematic placeholder
// rather than inventing footage.
export default function CameraThumbGrid({ cameras = [], activeCameraId, onSelect }) {
  const liveId = 'CAM_LIVE';

  return (
    <div className="flex flex-col overflow-hidden rounded-lg border border-hairline bg-panel">
      <div className="flex items-center justify-between border-b border-hairline px-3 py-2">
        <span className="mono text-[10px] tracking-[0.2em] uppercase text-ghost">Cameras</span>
        <span className="mono text-[10px] text-ghost">{cameras.length} feed{cameras.length === 1 ? '' : 's'}</span>
      </div>
      <div className="grid grid-cols-3 gap-2 p-2">
        {cameras.map((cam) => {
          const active = cam.id === activeCameraId;
          const isLiveSource = cam.id === liveId;
          return (
            <button
              key={cam.id}
              onClick={() => onSelect?.(cam.id)}
              className={`group relative overflow-hidden rounded-md border text-left transition-colors ${
                active ? 'border-live/60' : 'border-hairline hover:border-hairline-2'
              }`}
              title={cam.name}
            >
              <div className="relative aspect-video w-full bg-black">
                {isLiveSource ? (
                  <CamThumbLive />
                ) : (
                  <span className="flex h-full w-full items-center justify-center text-ghost/50">
                    <VideoOff className="h-3.5 w-3.5" />
                  </span>
                )}
                {active && (
                  <span className="absolute left-1 top-1 h-1.5 w-1.5 rounded-full bg-live shadow-[0_0_5px_1px_rgba(34,211,238,0.7)]" />
                )}
              </div>
              <div className="mono truncate px-1.5 py-1 text-[9px] uppercase tracking-wider text-ghost group-hover:text-dim">
                {cam.name}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function CamThumbLive() {
  const [broken, setBroken] = useState(false);
  if (broken) {
    return (
      <span className="flex h-full w-full items-center justify-center bg-[#070b11]">
        <VideoOff className="h-3.5 w-3.5 text-ghost/40" />
      </span>
    );
  }
  return (
    <img
      src={liveStreamUrl()}
      alt="Cam Live"
      className="h-full w-full object-cover opacity-80"
      onError={() => setBroken(true)}
    />
  );
}
