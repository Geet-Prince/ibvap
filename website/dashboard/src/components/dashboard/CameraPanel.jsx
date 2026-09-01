import MainFeed from './MainFeed';
import QuadView from './QuadView';

export default function CameraPanel({
  activeCamera,
  cameras,
  detections,
  onSelectCamera,
  feedOnline = true,
  humans,
  streamSrc,
}) {
  return (
    <section className="flex flex-col gap-3">
      <MainFeed
        cameraId={activeCamera?.id}
        cameraName={activeCamera?.name}
        streamSrc={streamSrc}
        detections={detections}
        offline={!feedOnline}
        humans={humans}
      />

      {/* 4-camera quad grid — raw MJPEG, auto-rotates highlight every 8s */}
      <div className="flex flex-col overflow-hidden rounded-lg border border-hairline bg-panel">
        <div className="flex items-center justify-between border-b border-hairline px-3 py-2">
          <span className="mono text-[10px] tracking-[0.2em] uppercase text-ghost">Live Cameras</span>
          <span className="mono text-[10px] text-ghost">{cameras.length} feed{cameras.length === 1 ? '' : 's'}</span>
        </div>
        <QuadView
          cameras={cameras}
          activeCameraId={activeCamera?.id}
          onSelect={onSelectCamera}
        />
      </div>
    </section>
  );
}
