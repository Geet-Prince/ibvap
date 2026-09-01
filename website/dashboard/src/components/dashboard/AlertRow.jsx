import { Activity, Camera, MapPin, Clock, FileDown } from 'lucide-react';
import { SEV_COLOR, relTime } from '../../lib/theme';
import { downloadIncidentReport } from '../../lib/pdfReport';

export default function AlertRow({ item, selected, onSelect }) {
  const color = SEV_COLOR[item.severity] || SEV_COLOR.informational;
  const thumb = item.snapshotUrl;
  const isIncident =
    item.kind === 'incident' ||
    item.snapshotCount != null ||
    item.modules?.length ||
    item.startedAt;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(item._id)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelect(item._id); }}
      className={`flex w-full items-start gap-3 border-b border-hairline/70 px-3 py-2.5 text-left transition-colors ${
        selected ? 'bg-hairline/25' : 'hover:bg-panel-2 cursor-pointer'
      }`}
    >
      <span className="mt-1 flex h-2 w-2 shrink-0 rounded-full" style={{ background: color, boxShadow: `0 0 6px 1px ${color}55` }} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-[12px] font-medium text-fg">{item.title}</span>
          <span className="shrink-0 rounded-sm px-1.5 py-0.5 mono text-[9px] font-semibold uppercase tracking-wider" style={{ background: `${color}22`, color }}>
            {item.dangerLabel || item.severity}
          </span>
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[10px] text-ghost">
          <span className="flex items-center gap-1">
            <MapPin className="h-2.5 w-2.5" />
            {item.location}
          </span>
          <span className="flex items-center gap-1">
            <Camera className="h-2.5 w-2.5" />
            {item.cameraName}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-2.5 w-2.5" />
            {relTime(item.timestamp)}
          </span>
          <span className="mx-1 h-3 w-px shrink-0 bg-hairline-2" />
          {item.confidence != null && (
            <span className="flex items-center gap-1 mono text-[9px] text-dim">
              <Activity className="h-2.5 w-2.5" />
              CON {item.confidence}%
            </span>
          )}
          {item.humansDetected > 0 && (
            <span className="mono text-[9px] text-nominal">👤 {item.humansDetected}</span>
          )}
          {item.status && item.status !== 'new' && (
            <span className="rounded-sm bg-hairline px-1 mono text-[9px] uppercase tracking-wider text-ghost">
              {item.status}
            </span>
          )}
          {isIncident && (
            <button
              onClick={(e) => { e.stopPropagation(); downloadIncidentReport(item); }}
              className="ml-auto flex items-center gap-1 rounded-sm border border-hairline/60 px-1.5 py-0.5 mono text-[9px] text-dim transition-colors hover:border-live/50 hover:text-live"
              title="Download PDF report"
            >
              <FileDown className="h-2.5 w-2.5" />
              PDF
            </button>
          )}
        </div>
      </div>
      {thumb && (
        <img
          src={thumb}
          alt=""
          className="h-11 w-11 shrink-0 rounded border border-hairline object-cover"
          onError={(e) => (e.currentTarget.style.display = 'none')}
        />
      )}
    </div>
  );
}
