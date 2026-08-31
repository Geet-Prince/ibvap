export default function AlertTabs({ tab, onChange, counts = {} }) {
  const tabs = [
    { id: 'alerts', label: 'Alerts', count: counts.alerts },
    { id: 'incidents', label: 'Incidents', count: counts.incidents },
  ];
  return (
    <div className="flex shrink-0 border-b border-hairline">
      {tabs.map((t) => {
        const active = tab === t.id;
        return (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            className={`flex items-center gap-2 border-b-2 px-4 py-2 text-[11px] font-medium uppercase tracking-wider transition-colors ${
              active
                ? 'border-live text-live'
                : 'border-transparent text-ghost hover:text-dim'
            }`}
          >
            {t.label}
            {t.count != null && (
              <span className={`rounded-full px-1.5 py-0.5 mono text-[9px] ${active ? 'bg-live/15 text-live' : 'bg-hairline text-ghost'}`}>
                {t.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
