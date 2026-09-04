import { ShieldCheck, Folder, ChevronDown, ChevronRight, Camera } from 'lucide-react';
import AlertRow from './AlertRow';
import { useState } from 'react';

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

function CameraFolder({ cameraId, items, selectedId, onSelect }) {
  const [open, setOpen] = useState(true);
  
  return (
    <div className="flex flex-col border-b border-hairline/50 last:border-b-0">
      <button 
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 bg-[#0a0e0b] px-3 py-2 text-left hover:bg-white/5 border-y border-hairline/30 sticky top-0 z-10"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5 text-ghost" /> : <ChevronRight className="h-3.5 w-3.5 text-ghost" />}
        <Folder className="h-3.5 w-3.5 text-live/70" fill="currentColor" fillOpacity={0.2} />
        <span className="mono text-[11px] font-semibold tracking-wider text-fg/90">{cameraId}</span>
        <span className="ml-auto rounded-full bg-white/10 px-1.5 py-0.5 mono text-[9px] text-ghost">
          {items.length}
        </span>
      </button>
      {open && (
        <div className="flex flex-col bg-panel">
          {items.map((item) => (
            <div key={item._id} className="pl-4 border-l-2 border-live/10 ml-4 relative">
              <div className="absolute left-[-2px] top-0 bottom-0 w-2" />
              <AlertRow item={item} selected={item._id === selectedId} onSelect={onSelect} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function AlertList({ items = [], loading = false, selectedId, onSelect, label = 'alerts' }) {
  if (loading) {
    return <div className="max-h-[460px] flex-1 overflow-y-auto"><Skeleton /></div>;
  }
  
  if (items.length === 0) {
    return <div className="max-h-[460px] flex-1 overflow-y-auto"><Empty label={label} /></div>;
  }

  // If showing incidents, group by camera
  if (label === 'incidents') {
    const groups = {};
    items.forEach(item => {
      const cam = item.cameraId || 'Unknown';
      if (!groups[cam]) groups[cam] = [];
      groups[cam].push(item);
    });
    
    return (
      <div className="max-h-[460px] flex-1 overflow-y-auto bg-panel-2">
        {Object.entries(groups).map(([cam, groupItems]) => (
          <CameraFolder 
            key={cam} 
            cameraId={cam} 
            items={groupItems} 
            selectedId={selectedId} 
            onSelect={onSelect} 
          />
        ))}
      </div>
    );
  }

  return (
    <div className="max-h-[460px] flex-1 overflow-y-auto">
      {items.map((item) => (
        <AlertRow key={item._id} item={item} selected={item._id === selectedId} onSelect={onSelect} />
      ))}
    </div>
  );
}
