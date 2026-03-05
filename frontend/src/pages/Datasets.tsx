import { useState, useEffect, useCallback } from 'react';
import { Upload, FileSpreadsheet, Check, AlertCircle } from 'lucide-react';
import { uploadDataset, getDatasets, type Dataset } from '../services/api';

export default function Datasets() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadDatasets = useCallback(async () => {
    const res = await getDatasets();
    setDatasets(res.datasets);
  }, []);

  useEffect(() => { loadDatasets(); }, [loadDatasets]);

  const handleFile = async (file: File) => {
    if (!file.name.endsWith('.csv')) {
      setMessage({ type: 'error', text: 'Only CSV files are accepted' });
      return;
    }
    setUploading(true);
    setMessage(null);
    try {
      await uploadDataset(file);
      setMessage({ type: 'success', text: `"${file.name}" uploaded successfully` });
      await loadDatasets();
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.response?.data?.detail || 'Upload failed' });
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Datasets</h1>
        <p className="text-slate-400 mt-1">Upload and manage your CSV datasets</p>
      </div>

      {/* Upload zone */}
      <div
        className={`glass-card p-10 border-2 border-dashed transition-all cursor-pointer ${
          dragActive ? 'border-brand-500 bg-brand-500/5' : 'border-slate-700 hover:border-slate-600'
        }`}
        onDragOver={e => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        onClick={() => {
          const input = document.createElement('input');
          input.type = 'file';
          input.accept = '.csv';
          input.onchange = (e: any) => { if (e.target.files[0]) handleFile(e.target.files[0]); };
          input.click();
        }}
      >
        <div className="flex flex-col items-center gap-3">
          {uploading ? (
            <div className="w-10 h-10 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          ) : (
            <Upload size={36} className="text-slate-500" />
          )}
          <p className="text-slate-300 font-medium">{uploading ? 'Uploading...' : 'Drop CSV file here or click to browse'}</p>
          <p className="text-xs text-slate-500">Maximum 50MB</p>
        </div>
      </div>

      {message && (
        <div className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm ${
          message.type === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
        }`}>
          {message.type === 'success' ? <Check size={16} /> : <AlertCircle size={16} />}
          {message.text}
        </div>
      )}

      {/* Dataset list */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800/60">
          <h3 className="text-sm font-semibold text-slate-300">Uploaded Datasets ({datasets.length})</h3>
        </div>
        {datasets.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No datasets uploaded yet. Upload a CSV file above.
          </div>
        ) : (
          <div className="divide-y divide-slate-800/50">
            {datasets.map(ds => (
              <div key={ds.id} className="px-6 py-4 hover:bg-slate-800/20 transition-colors">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-brand-600/15 flex items-center justify-center flex-shrink-0">
                    <FileSpreadsheet size={18} className="text-brand-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{ds.name}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {ds.num_rows?.toLocaleString()} rows · {ds.num_columns} columns · {new Date(ds.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    {ds.columns_info && Object.keys(ds.columns_info).slice(0, 5).map(col => (
                      <span key={col} className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700">
                        {col}
                      </span>
                    ))}
                    {ds.columns_info && Object.keys(ds.columns_info).length > 5 && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono text-slate-500">
                        +{Object.keys(ds.columns_info).length - 5} more
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
