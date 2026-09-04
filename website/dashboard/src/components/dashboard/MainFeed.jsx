import { useState, useRef, useEffect, useCallback } from 'react';
import { VideoOff, Edit3, Save, X, Trash2 } from 'lucide-react';
import { useClock } from '../../hooks/useClock';
import { liveStreamUrl, API_BASE } from '../../lib/config';

const BOX_COLOR = {
  critical: '#ef4444',
  high: '#ff8a3d',
  medium: '#f5a623',
  low: '#2ecc71',
  nominal: '#2ecc71',
};

export default function MainFeed({ cameraId, streamSrc, detections = [], cameraName, offline = false, humans }) {
  // dims from the MAIN feed image (used for detection box overlays on the main feed)
  const [dims, setDims] = useState(null);
  const [streamBroken, setStreamBroken] = useState(false);

  // Fence Editor State
  const [isEditingFence, setIsEditingFence] = useState(false);
  const [polygon, setPolygon] = useState([]);

  // editDims = natural resolution of the image as rendered inside the modal editor.
  // This is separate from dims so resizing/re-rendering the modal image does not
  // corrupt the main-feed detection box calculations.
  const [editDims, setEditDims] = useState(null);

  // imgRef  -> the main-feed <img> (used for detection box overlays)
  // editRef -> the modal-editor <img> (used for click-to-polygon coordinate mapping)
  const imgRef = useRef(null);
  const editRef = useRef(null);

  // Fetch existing polygon when editor opens
  useEffect(() => {
    if (isEditingFence && cameraId) {
      fetch(`${API_BASE}/api/cameras/${cameraId}/fence`)
        .then(res => res.json())
        .then(data => {
          if (data.polygon && data.polygon.length > 0) setPolygon(data.polygon);
          else setPolygon([]);
        })
        .catch(console.error);
    }
  }, [isEditingFence, cameraId]);

  // ---- Accurate click-to-polygon coordinate mapping ----
  // The modal editor renders the MJPEG stream at an arbitrary CSS size.
  // We MUST measure the rendered rect of the *editor* image, NOT the main feed.
  // editDims holds the stream's natural (pixel) dimensions so we can scale correctly.
  const handleEditorClick = useCallback((e) => {
    if (!editRef.current) return;
    const rect = editRef.current.getBoundingClientRect();

    // Pixel offset of click inside the rendered image element
    const px = e.clientX - rect.left;
    const py = e.clientY - rect.top;

    // Guard: click must be inside the image bounds
    if (px < 0 || py < 0 || px > rect.width || py > rect.height) return;

    if (editDims) {
      // Scale from CSS pixels → video stream pixels
      const scaleX = editDims.nw / rect.width;
      const scaleY = editDims.nh / rect.height;
      setPolygon(prev => [...prev, [Math.round(px * scaleX), Math.round(py * scaleY)]]);
    } else {
      // Fallback: store as fractions (0..1) until the image loads
      setPolygon(prev => [...prev, [Math.round(px), Math.round(py)]]);
    }
  }, [editDims]);

  const removeLastPoint = () => setPolygon(prev => prev.slice(0, -1));

  const savePolygon = async () => {
    if (!cameraId) return;
    try {
      await fetch(`${API_BASE}/api/cameras/${cameraId}/fence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ polygon })
      });
      setIsEditingFence(false);
    } catch (e) {
      console.error(e);
    }
  };

  const now = useClock(1000);
  const time = now.toLocaleTimeString('en-GB', { hour12: false });

  const src = streamSrc ?? liveStreamUrl();
  const ratio = dims ? `${dims.nw} / ${dims.nh}` : '16 / 9';

  const humansCount = humans != null ? humans : null;
  const down = offline || streamBroken;

  return (
    <div className="flex flex-col overflow-hidden rounded-lg border border-hairline bg-panel">
      <div className="flex items-center justify-between border-b border-hairline px-3 py-2">
        <span className="mono text-[10px] tracking-[0.2em] uppercase text-ghost">Live Feed</span>
        <span className="flex items-center gap-2">
          <span className="mono text-[10px] uppercase tracking-wider text-ghost">{cameraName || cameraId || 'All Cameras'}</span>
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
          <div className="flex h-full w-full items-center justify-center bg-[#090e0a]">
            <VideoOff className="h-8 w-8 text-ghost/40" />
          </div>
        ) : (
          <img
            ref={imgRef}
            key={src}
            src={src}
            alt="live"
            className="h-full w-full object-contain"
            onLoad={(e) => {
              const el = e.currentTarget;
              setStreamBroken(false);
              setDims({ nw: Math.max(el.naturalWidth, 1), nh: Math.max(el.naturalHeight, 1) });
            }}
            onError={() => setStreamBroken(true)}
          />
        )}

        {cameraId && !isEditingFence && (
          <div className="absolute right-1.5 top-1.5 flex gap-1">
            <button
              onClick={() => setIsEditingFence(true)}
              className="rounded bg-black/55 p-1 text-ghost hover:text-white"
              title="Edit Virtual Fence"
            >
              <Edit3 className="h-4 w-4" />
            </button>
          </div>
        )}

        <div className="pointer-events-none absolute left-1.5 top-1.5 flex flex-col gap-1">
          <span className="rounded-sm bg-black/55 px-1.5 py-0.5 mono text-[9px] tracking-[0.15em] text-live">
            ● {down ? 'OFFLINE' : 'REC'}
          </span>
          <span className="w-max rounded-sm bg-black/55 px-1.5 py-0.5 mono text-[9px] tracking-[0.15em] text-fg/80">
            LIVE OBJECTS: {humansCount != null ? humansCount : '--'}
          </span>
        </div>

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

      {/* ── Full-screen Fence Editor Modal ── */}
      {isEditingFence && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4 sm:p-12 backdrop-blur-sm">
          <div className="flex max-h-full max-w-full flex-col overflow-hidden rounded-lg bg-panel border border-hairline shadow-2xl w-full" style={{ maxWidth: '90vw', maxHeight: '90vh' }}>
            {/* Header */}
            <div className="flex items-center justify-between border-b border-hairline px-4 py-3 bg-[#090e0a] flex-shrink-0">
              <div className="flex flex-col">
                <span className="mono text-xs uppercase text-ghost tracking-widest">
                  Restricted Zone Editor — {cameraName || cameraId}
                </span>
                <span className="mono text-[10px] text-ghost/60 mt-0.5">
                  Click on the image to add polygon points. Right-click or use Undo to remove the last point.
                  {polygon.length > 0 ? ` (${polygon.length} point${polygon.length > 1 ? 's' : ''})` : ''}
                </span>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={removeLastPoint}
                  disabled={polygon.length === 0}
                  className="flex items-center gap-1.5 rounded bg-yellow-600/80 px-3 py-1.5 text-xs text-white hover:bg-yellow-600 disabled:opacity-40 disabled:cursor-not-allowed"
                  title="Undo last point"
                >
                  Undo
                </button>
                <button
                  onClick={() => setPolygon([])}
                  className="flex items-center gap-1.5 rounded bg-red-600/80 px-3 py-1.5 text-xs text-white hover:bg-red-600"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Clear
                </button>
                <button
                  onClick={savePolygon}
                  disabled={polygon.length < 3}
                  className="flex items-center gap-1.5 rounded bg-green-600/80 px-3 py-1.5 text-xs text-white hover:bg-green-600 disabled:opacity-40 disabled:cursor-not-allowed"
                  title={polygon.length < 3 ? 'Need at least 3 points' : 'Save fence polygon'}
                >
                  <Save className="h-4 w-4" /> Save
                </button>
                <button
                  onClick={() => setIsEditingFence(false)}
                  className="rounded bg-white/10 px-3 py-1.5 text-xs text-white hover:bg-white/20 ml-2"
                >
                  Cancel
                </button>
              </div>
            </div>

            {/* Editor canvas — fills all remaining space */}
            <div className="relative flex-1 bg-black overflow-hidden flex items-center justify-center" style={{ minHeight: 0 }}>
              {/* Wrapper constrains the image to its natural aspect ratio */}
              <div
                className="relative"
                style={{
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <div
                  className="relative"
                  style={{
                    /* keep the image in its native aspect ratio */
                    aspectRatio: editDims ? `${editDims.nw} / ${editDims.nh}` : '16 / 9',
                    maxWidth: '100%',
                    maxHeight: '100%',
                    position: 'relative',
                  }}
                >
                  {/* The live video stream used for click-to-draw */}
                  <img
                    ref={editRef}
                    src={src}
                    alt="fence editor"
                    className="block w-full h-full object-fill cursor-crosshair select-none"
                    draggable={false}
                    onLoad={(e) => {
                      const el = e.currentTarget;
                      const nw = Math.max(el.naturalWidth, 1);
                      const nh = Math.max(el.naturalHeight, 1);
                      setEditDims({ nw, nh });
                    }}
                    onClick={handleEditorClick}
                    onContextMenu={(e) => { e.preventDefault(); removeLastPoint(); }}
                  />

                  {/* SVG overlay — drawn in the same coordinate space as the image */}
                  <svg
                    className="absolute inset-0 w-full h-full pointer-events-none"
                    viewBox={editDims ? `0 0 ${editDims.nw} ${editDims.nh}` : '0 0 1 1'}
                    preserveAspectRatio="none"
                  >
                    {/* Filled polygon */}
                    {polygon.length >= 3 && (
                      <polygon
                        points={polygon.map(p => `${p[0]},${p[1]}`).join(' ')}
                        fill="rgba(255,0,0,0.18)"
                        stroke="red"
                        strokeWidth={editDims ? editDims.nw * 0.003 : 3}
                        strokeLinejoin="round"
                      />
                    )}
                    {/* Line-in-progress (open polyline) */}
                    {polygon.length >= 2 && (
                      <polyline
                        points={polygon.map(p => `${p[0]},${p[1]}`).join(' ')}
                        fill="none"
                        stroke="red"
                        strokeWidth={editDims ? editDims.nw * 0.003 : 3}
                        strokeDasharray={polygon.length < 3 ? '8 4' : 'none'}
                      />
                    )}
                    {/* Vertex dots + index labels */}
                    {polygon.map((p, i) => (
                      <g key={i}>
                        <circle
                          cx={p[0]}
                          cy={p[1]}
                          r={editDims ? editDims.nw * 0.008 : 6}
                          fill={i === 0 ? '#00ff88' : 'red'}
                          stroke="white"
                          strokeWidth={editDims ? editDims.nw * 0.002 : 2}
                        />
                        <text
                          x={p[0] + (editDims ? editDims.nw * 0.012 : 8)}
                          y={p[1] - (editDims ? editDims.nh * 0.012 : 8)}
                          fill="white"
                          fontSize={editDims ? editDims.nw * 0.018 : 14}
                          fontFamily="monospace"
                          fontWeight="bold"
                          style={{ textShadow: '0 0 3px black' }}
                        >
                          {i === 0 ? 'START' : i}
                        </text>
                      </g>
                    ))}
                    {/* Closing line preview */}
                    {polygon.length >= 3 && (
                      <line
                        x1={polygon[polygon.length - 1][0]}
                        y1={polygon[polygon.length - 1][1]}
                        x2={polygon[0][0]}
                        y2={polygon[0][1]}
                        stroke="rgba(255,0,0,0.5)"
                        strokeWidth={editDims ? editDims.nw * 0.002 : 2}
                        strokeDasharray="6 3"
                      />
                    )}
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
