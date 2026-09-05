import { useState, useEffect } from 'react';
import { Users, Upload, X, Check, AlertTriangle } from 'lucide-react';

export default function PersonnelManager({ onClose }) {
  const [personnel, setPersonnel] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  
  const [name, setName] = useState('');
  const [badge, setBadge] = useState('');
  const [file, setFile] = useState(null);

  useEffect(() => {
    fetchPersonnel();
  }, []);

  const fetchPersonnel = async () => {
    try {
      const res = await fetch('/api/personnel');
      const data = await res.json();
      if (data.status === 'success') {
        setPersonnel(data.data);
      }
    } catch (err) {
      setError('Failed to fetch personnel list.');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!name || !file) {
      setError('Name and Image are required.');
      return;
    }
    
    setUploading(true);
    setError('');
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('badge_number', badge);
    formData.append('file', file);

    try {
      const res = await fetch('/api/personnel', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed');
      }
      setName('');
      setBadge('');
      setFile(null);
      fetchPersonnel();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="flex w-full max-w-2xl flex-col overflow-hidden rounded-lg border border-hairline bg-panel shadow-2xl">
        <div className="flex items-center justify-between border-b border-hairline px-4 py-3">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-live" />
            <h2 className="text-[15px] font-semibold text-fg">Authorized Personnel Management</h2>
          </div>
          <button onClick={onClose} className="rounded p-1 hover:bg-white/10 text-ghost hover:text-fg">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex flex-col md:flex-row min-h-[400px]">
          {/* Add Form */}
          <div className="w-full md:w-1/2 border-b md:border-b-0 md:border-r border-hairline p-4 bg-panel-2">
            <h3 className="mono text-[11px] font-semibold tracking-wider text-ghost uppercase mb-4">Add New Authorized Person</h3>
            
            <form onSubmit={handleUpload} className="flex flex-col gap-4">
              <label className="flex flex-col gap-1">
                <span className="mono text-[10px] uppercase text-dim">Full Name *</span>
                <input 
                  type="text" 
                  value={name} 
                  onChange={e => setName(e.target.value)}
                  className="rounded border border-hairline bg-panel px-3 py-1.5 text-[13px] text-fg outline-none focus:border-live"
                  placeholder="e.g. Soldier Ram"
                  required
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="mono text-[10px] uppercase text-dim">Badge Number</span>
                <input 
                  type="text" 
                  value={badge} 
                  onChange={e => setBadge(e.target.value)}
                  className="rounded border border-hairline bg-panel px-3 py-1.5 text-[13px] text-fg outline-none focus:border-live"
                  placeholder="Optional ID"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="mono text-[10px] uppercase text-dim">Face Image (Clear, Front-facing) *</span>
                <input 
                  type="file" 
                  accept="image/*"
                  onChange={e => setFile(e.target.files[0])}
                  className="rounded border border-hairline bg-panel px-3 py-1.5 text-[12px] text-fg outline-none focus:border-live file:mr-2 file:border-0 file:bg-white/10 file:px-2 file:py-1 file:text-[11px] file:text-fg file:rounded-sm hover:file:bg-white/20"
                  required
                />
              </label>

              {error && (
                <div className="flex items-center gap-2 rounded bg-sev-critical/20 px-3 py-2 text-[12px] text-sev-critical">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <button 
                type="submit" 
                disabled={uploading}
                className="mt-2 flex items-center justify-center gap-2 rounded bg-live px-4 py-2 text-[13px] font-semibold text-black transition-colors hover:bg-live/90 disabled:opacity-50"
              >
                {uploading ? (
                  <span className="animate-pulse">Analyzing Face...</span>
                ) : (
                  <>
                    <Upload className="h-4 w-4" /> Add to Database
                  </>
                )}
              </button>
            </form>
          </div>

          {/* List */}
          <div className="w-full md:w-1/2 p-4 flex flex-col">
            <h3 className="mono text-[11px] font-semibold tracking-wider text-ghost uppercase mb-4">Known Personnel Registry</h3>
            <div className="flex-1 overflow-y-auto">
              {loading ? (
                <div className="text-[12px] text-dim animate-pulse">Loading database...</div>
              ) : personnel.length === 0 ? (
                <div className="text-[12px] text-dim text-center mt-10">No authorized personnel found.</div>
              ) : (
                <div className="flex flex-col gap-2">
                  {personnel.map(p => (
                    <div key={p.id} className="flex items-center gap-3 rounded border border-hairline/50 bg-panel-2 p-2">
                      <img src={p.image_path} alt="" className="h-10 w-10 shrink-0 rounded-full border border-live object-cover" />
                      <div className="flex flex-col">
                        <span className="text-[13px] font-medium text-fg">{p.name}</span>
                        {p.badge_number && <span className="mono text-[10px] text-ghost">Badge: {p.badge_number}</span>}
                      </div>
                      <Check className="ml-auto h-4 w-4 text-live" />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
