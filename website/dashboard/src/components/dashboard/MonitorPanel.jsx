import { useState } from 'react';
import RadarMap from './RadarMap';
import AlertTabs from './AlertTabs';
import AlertList from './AlertList';

export default function MonitorPanel({
  alerts = [],
  incidents = [],
  points = [],
  alertsLoading,
  incidentsLoading,
  selectedId,
  onSelect,
  streamSrc,
}) {
  const [tab, setTab] = useState('alerts');
  const items = tab === 'alerts' ? alerts : incidents;
  const loading = tab === 'alerts' ? alertsLoading : incidentsLoading;

  return (
    <section className="flex min-w-0 flex-col gap-3">
      <div className="flex gap-3 h-[360px]">
        {streamSrc && (
          <div className="flex-1 overflow-hidden rounded-lg border border-hairline bg-panel flex items-center justify-center relative">
            <div className="absolute top-0 left-0 right-0 p-2 z-10 bg-gradient-to-b from-black/60 to-transparent">
               <span className="mono text-[10px] tracking-[0.2em] uppercase text-ghost">AI Target Lock</span>
            </div>
            <img src={streamSrc} alt="AI Camera Feed" className="w-full h-full object-contain" />
          </div>
        )}
        <div className={streamSrc ? "w-[280px] shrink-0 flex flex-col" : "w-full"}>
          <RadarMap
            points={points}
            selectedId={selectedId}
            onSelectPoint={(item) => onSelect?.(item._id)}
          />
        </div>
      </div>
      <div className="flex flex-col overflow-hidden rounded-lg border border-hairline bg-panel">
        <AlertTabs
          tab={tab}
          onChange={setTab}
          counts={{ alerts: alerts.length, incidents: incidents.length }}
        />
        <AlertList
          items={items}
          loading={loading}
          selectedId={selectedId}
          onSelect={onSelect}
          label={tab}
        />
      </div>
    </section>
  );
}
