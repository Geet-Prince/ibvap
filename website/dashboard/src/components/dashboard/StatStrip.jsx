import StatCard from './StatCard';

export default function StatStrip({ stats = [] }) {
  if (stats.length === 0) {
    return (
      <div className="grid grid-cols-3 gap-3 md:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-[82px] animate-pulse rounded-lg border border-hairline bg-panel" />
        ))}
      </div>
    );
  }
  return (
    <div className="flex flex-wrap gap-3">
      {stats.map((s) => (
        <StatCard key={s.key} {...s} />
      ))}
    </div>
  );
}
