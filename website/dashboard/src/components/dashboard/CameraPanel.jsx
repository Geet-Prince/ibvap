import MainFeed from './MainFeed';
import CameraThumbGrid from './CameraThumbGrid';

export default function CameraPanel({
  activeCamera,
  cameras,
  detections,
  onSelectCamera,
  feedOnline = true,
  humans,
}) {
  return (
    <section className="flex flex-col gap-3">
      <MainFeed
        cameraId={activeCamera?.id}
        cameraName={activeCamera?.name}
        detections={detections}
        offline={!feedOnline}
        humans={humans}
      />
      <CameraThumbGrid
        cameras={cameras}
        activeCameraId={activeCamera?.id}
        onSelect={onSelectCamera}
      />
    </section>
  );
}
