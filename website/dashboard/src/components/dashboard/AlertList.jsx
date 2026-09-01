import { ShieldCheck } from 'lucide-react';
import AlertRow from './AlertRow';

function Skeleton({ count = 6 }) {
  return (
    <div className="flex flex-col">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 border-b border-hairline/70 px-3 py-3">
          <div className="h-2 w-2 animate-pulse rounded-full bg-hairline-2" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-2/3 animate-pulse rounded bg-hairline-2" />
            <div className="h-2 w-1/2 animate-pulse rounded bg-hairline" />
            <div className="flex gap-2">
              <div className="h-2 w-12 animate-pulse rounded bg-hairline" />
              <div className="h-2 w-12 animate-pulse rounded bg-hairline" />
            </div>
          </div>
          <div className="h-10 w-10 animate-pulse rounded bg-hairline" />
        </div>
      ))}
    </div>
  );
}

function Empty({ label }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      <ShieldCheck className="h-8 w-8 text-nominal/50" />
      <div>
        <div className="text-[13px] font-medium text-fg/80">No active {label}</div>
        <div className="mt-1 text-[11px] text-ghost">All clear. New activity will appear here.</div>
      </div>
    </div>
  );
}

export default function AlertList({ items = [], loading = false, selectedId, onSelect, label = 'alerts' }) {
  return (
    <div className="max-h-[460px] flex-1 overflow-y-auto">
      {loading ? (
        <Skeleton />
      ) : items.length === 0 ? (
        <Empty label={label} />
      ) : (
        items.map((item) => (
          <AlertRow key={item._id} item={item} selected={item._id === selectedId} onSelect={onSelect} />
        ))
      )}
    </div>
  );
}
