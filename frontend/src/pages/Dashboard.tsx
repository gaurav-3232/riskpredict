import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { Database, FlaskConical, Crosshair, TrendingUp } from 'lucide-react';
import { getExperiments, getDatasets, type Experiment, type Dataset } from '../services/api';

export default function Dashboard() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getExperiments(), getDatasets()])
      .then(([expRes, dsRes]) => {
        setExperiments(expRes.experiments);
        setDatasets(dsRes.datasets);
      })
      .finally(() => setLoading(false));
  }, []);

  const completed = experiments.filter(e => e.status === 'completed');
  const avgAccuracy = completed.length
    ? completed.reduce((s, e) => s + (e.metrics_json?.accuracy || 0), 0) / completed.length
    : 0;

  const comparisonData = completed.map(e => ({
    name: `#${e.id} ${e.model_type.replace('_', ' ')}`,
    accuracy: +(e.metrics_json?.accuracy || 0).toFixed(3),
    f1: +(e.metrics_json?.f1_score || 0).toFixed(3),
    precision: +(e.metrics_json?.precision || 0).toFixed(3),
    recall: +(e.metrics_json?.recall || 0).toFixed(3),
  }));

  const bestExperiment = completed.reduce<Experiment | null>((best, e) => {
    if (!best || (e.metrics_json?.f1_score || 0) > (best.metrics_json?.f1_score || 0)) return e;
    return best;
  }, null);

  const radarData = bestExperiment?.metrics_json
    ? [
        { metric: 'Accuracy', value: bestExperiment.metrics_json.accuracy },
        { metric: 'Precision', value: bestExperiment.metrics_json.precision },
        { metric: 'Recall', value: bestExperiment.metrics_json.recall },
        { metric: 'F1', value: bestExperiment.metrics_json.f1_score },
        { metric: 'ROC AUC', value: bestExperiment.metrics_json.roc_auc },
      ]
    : [];

  const stats = [
    { label: 'Datasets', value: datasets.length, icon: Database, color: 'text-emerald-400' },
    { label: 'Experiments', value: experiments.length, icon: FlaskConical, color: 'text-brand-400' },
    { label: 'Completed', value: completed.length, icon: Crosshair, color: 'text-amber-400' },
    { label: 'Avg Accuracy', value: `${(avgAccuracy * 100).toFixed(1)}%`, icon: TrendingUp, color: 'text-rose-400' },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-slate-400 mt-1">Overview of your ML experiments</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="glass-card p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-slate-400">{label}</span>
              <Icon size={18} className={color} />
            </div>
            <p className="text-2xl font-bold text-white">{value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Model Comparison</h3>
          {comparisonData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={comparisonData} barCategoryGap="20%">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} angle={-15} textAnchor="end" height={60} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} domain={[0, 1]} />
                <Tooltip
                  contentStyle={{ background: '#1a2035', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                  labelStyle={{ color: '#e2e8f0' }}
                />
                <Bar dataKey="accuracy" fill="#338dfc" radius={[4, 4, 0, 0]} name="Accuracy" />
                <Bar dataKey="f1" fill="#10b981" radius={[4, 4, 0, 0]} name="F1 Score" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-slate-500 text-sm">
              No experiments yet. Train a model to see comparisons.
            </div>
          )}
        </div>

        <div className="glass-card p-6">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">
            Best Model Metrics
            {bestExperiment && <span className="text-slate-500 font-normal ml-2">(Experiment #{bestExperiment.id})</span>}
          </h3>
          {radarData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#1e293b" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <PolarRadiusAxis domain={[0, 1]} tick={{ fill: '#64748b', fontSize: 10 }} />
                <Radar dataKey="value" stroke="#338dfc" fill="#338dfc" fillOpacity={0.2} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[300px] text-slate-500 text-sm">
              No completed experiments yet.
            </div>
          )}
        </div>
      </div>

      {completed.length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Recent Experiments</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b border-slate-800">
                  <th className="pb-3 font-medium">ID</th>
                  <th className="pb-3 font-medium">Model</th>
                  <th className="pb-3 font-medium">Target</th>
                  <th className="pb-3 font-medium">Accuracy</th>
                  <th className="pb-3 font-medium">F1</th>
                  <th className="pb-3 font-medium">ROC AUC</th>
                  <th className="pb-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {completed.slice(0, 10).map(e => (
                  <tr key={e.id} className="border-b border-slate-800/50 text-slate-300">
                    <td className="py-3 font-mono text-xs">#{e.id}</td>
                    <td className="py-3">{e.model_type.replace(/_/g, ' ')}</td>
                    <td className="py-3 font-mono text-xs">{e.target_column}</td>
                    <td className="py-3 font-mono">{(e.metrics_json?.accuracy || 0).toFixed(4)}</td>
                    <td className="py-3 font-mono">{(e.metrics_json?.f1_score || 0).toFixed(4)}</td>
                    <td className="py-3 font-mono">{(e.metrics_json?.roc_auc || 0).toFixed(4)}</td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 rounded-full text-xs bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
                        {e.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
