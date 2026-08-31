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
}) {
  const [tab, setTab] = useState('alerts');
  const items = tab === 'alerts' ? alerts : incidents;
  const loading = tab === 'alerts' ? alertsLoading : incidentsLoading;

  return (
    <section className="flex min-w-0 flex-col gap-3">
      <RadarMap
        points={points}
        selectedId={selectedId}
        onSelectPoint={(item) => onSelect?.(item._id)}
      />
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
