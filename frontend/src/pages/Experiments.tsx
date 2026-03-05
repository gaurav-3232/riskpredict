import { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts';
import { FlaskConical, Play, ChevronDown, ChevronUp } from 'lucide-react';
import { getDatasets, getExperiments, trainModel, type Dataset, type Experiment } from '../services/api';

const MODEL_OPTIONS = [
  { value: 'logistic_regression', label: 'Logistic Regression' },
  { value: 'random_forest', label: 'Random Forest' },
  { value: 'gradient_boosting', label: 'Gradient Boosting' },
];

function ConfusionMatrix({ matrix, labels }: { matrix: number[][]; labels: string[] }) {
  const maxVal = Math.max(...matrix.flat());
  return (
    <div className="overflow-x-auto">
      <table className="text-xs">
        <thead>
          <tr>
            <th className="p-2 text-slate-500">Actual \ Pred</th>
            {labels.map(l => <th key={l} className="p-2 text-slate-400 font-mono">{l}</th>)}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              <td className="p-2 text-slate-400 font-mono font-medium">{labels[i]}</td>
              {row.map((val, j) => {
                const intensity = maxVal > 0 ? val / maxVal : 0;
                const isCorrect = i === j;
                return (
                  <td key={j} className="p-2 text-center font-mono" style={{
                    backgroundColor: isCorrect
                      ? `rgba(16, 185, 129, ${intensity * 0.5})`
                      : `rgba(239, 68, 68, ${intensity * 0.4})`,
                    color: intensity > 0.5 ? '#fff' : '#94a3b8',
                  }}>
                    {val}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ExperimentDetail({ experiment }: { experiment: Experiment }) {
  const [expanded, setExpanded] = useState(false);
  const m = experiment.metrics_json;
  if (!m) return null;

  const rocData = m.roc_curve
    ? m.roc_curve.fpr.map((fpr, i) => ({ fpr, tpr: m.roc_curve!.tpr[i] }))
    : [];

  const importanceData = m.feature_importance
    ? Object.entries(m.feature_importance)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 15)
        .map(([name, value]) => ({ name, value: +value.toFixed(4) }))
    : [];

  return (
    <div className="glass-card overflow-hidden">
      <button
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-800/20 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          <div className="w-9 h-9 rounded-lg bg-brand-600/15 flex items-center justify-center">
            <FlaskConical size={16} className="text-brand-400" />
          </div>
          <div className="text-left">
            <p className="text-sm font-medium text-white">
              Experiment #{experiment.id} — {experiment.model_type.replace(/_/g, ' ')}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              Target: {experiment.target_column} · Accuracy: {(m.accuracy * 100).toFixed(2)}% · F1: {(m.f1_score * 100).toFixed(2)}%
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-2 py-0.5 rounded-full text-xs ${
            experiment.status === 'completed'
              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
              : 'bg-red-500/15 text-red-400 border border-red-500/20'
          }`}>
            {experiment.status}
          </span>
          {expanded ? <ChevronUp size={16} className="text-slate-500" /> : <ChevronDown size={16} className="text-slate-500" />}
        </div>
      </button>

      {expanded && (
        <div className="px-6 pb-6 border-t border-slate-800/60 pt-4 space-y-6">
          {/* Metrics cards */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {[
              { label: 'Accuracy', value: m.accuracy },
              { label: 'Precision', value: m.precision },
              { label: 'Recall', value: m.recall },
              { label: 'F1 Score', value: m.f1_score },
              { label: 'ROC AUC', value: m.roc_auc },
            ].map(({ label, value }) => (
              <div key={label} className="bg-slate-800/50 rounded-lg p-3 text-center">
                <p className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</p>
                <p className="text-lg font-bold text-white mt-1 font-mono">{(value * 100).toFixed(2)}%</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* ROC Curve */}
            {rocData.length > 0 && (
              <div className="bg-slate-800/30 rounded-lg p-4">
                <h4 className="text-xs font-semibold text-slate-400 mb-3 uppercase tracking-wider">ROC Curve</h4>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={rocData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="fpr" tick={{ fill: '#64748b', fontSize: 10 }} label={{ value: 'FPR', position: 'bottom', fill: '#64748b', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#64748b', fontSize: 10 }} label={{ value: 'TPR', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#1a2035', border: '1px solid #334155', borderRadius: 8, fontSize: 11 }} />
                    <Line type="monotone" dataKey="tpr" stroke="#338dfc" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="fpr" stroke="#475569" strokeWidth={1} strokeDasharray="4 4" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Confusion Matrix */}
            <div className="bg-slate-800/30 rounded-lg p-4">
              <h4 className="text-xs font-semibold text-slate-400 mb-3 uppercase tracking-wider">Confusion Matrix</h4>
              <ConfusionMatrix matrix={m.confusion_matrix.matrix} labels={m.confusion_matrix.labels} />
            </div>

            {/* Feature Importance */}
            {importanceData.length > 0 && (
              <div className="bg-slate-800/30 rounded-lg p-4">
                <h4 className="text-xs font-semibold text-slate-400 mb-3 uppercase tracking-wider">Feature Importance</h4>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={importanceData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis type="number" tick={{ fill: '#64748b', fontSize: 10 }} />
                    <YAxis dataKey="name" type="category" tick={{ fill: '#94a3b8', fontSize: 10 }} width={90} />
                    <Tooltip contentStyle={{ background: '#1a2035', border: '1px solid #334155', borderRadius: 8, fontSize: 11 }} />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                      {importanceData.map((_, i) => (
                        <Cell key={i} fill={i === 0 ? '#338dfc' : i < 3 ? '#1d6ef1' : '#1e40af'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Experiments() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [datasetId, setDatasetId] = useState<number | ''>('');
  const [modelType, setModelType] = useState('random_forest');
  const [targetColumn, setTargetColumn] = useState('');
  const [testSize, setTestSize] = useState(0.2);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState('');

  const selectedDataset = datasets.find(d => d.id === datasetId);
  const columns = selectedDataset?.columns_info ? Object.keys(selectedDataset.columns_info) : [];

  useEffect(() => {
    getDatasets().then(res => setDatasets(res.datasets));
    getExperiments().then(res => setExperiments(res.experiments));
  }, []);

  const handleTrain = async () => {
    if (!datasetId || !targetColumn) {
      setError('Select a dataset and target column');
      return;
    }
    setTraining(true);
    setError('');
    try {
      await trainModel({ dataset_id: datasetId as number, model_type: modelType, target_column: targetColumn, test_size: testSize });
      const res = await getExperiments();
      setExperiments(res.experiments);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Training failed');
    } finally {
      setTraining(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Experiments</h1>
        <p className="text-slate-400 mt-1">Train models and analyze results</p>
      </div>

      {/* Training form */}
      <div className="glass-card p-6">
        <h3 className="text-sm font-semibold text-slate-300 mb-4">New Experiment</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs text-slate-500 mb-1.5">Dataset</label>
            <select
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500"
              value={datasetId}
              onChange={e => { setDatasetId(Number(e.target.value)); setTargetColumn(''); }}
            >
              <option value="">Select dataset...</option>
              {datasets.map(d => <option key={d.id} value={d.id}>{d.name} ({d.num_rows} rows)</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1.5">Target Column</label>
            <select
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500"
              value={targetColumn}
              onChange={e => setTargetColumn(e.target.value)}
              disabled={!datasetId}
            >
              <option value="">Select target...</option>
              {columns.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1.5">Model Type</label>
            <select
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500"
              value={modelType}
              onChange={e => setModelType(e.target.value)}
            >
              {MODEL_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1.5">Test Size ({(testSize * 100).toFixed(0)}%)</label>
            <input
              type="range"
              min="0.1"
              max="0.5"
              step="0.05"
              value={testSize}
              onChange={e => setTestSize(parseFloat(e.target.value))}
              className="w-full mt-2 accent-brand-500"
            />
          </div>
        </div>

        {error && <p className="text-red-400 text-sm mt-3">{error}</p>}

        <button
          className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
          onClick={handleTrain}
          disabled={training || !datasetId || !targetColumn}
        >
          {training ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Play size={16} />
          )}
          {training ? 'Training...' : 'Train Model'}
        </button>
      </div>

      {/* Experiments list */}
      <div className="space-y-3">
        {experiments.length === 0 ? (
          <div className="glass-card p-12 text-center text-slate-500 text-sm">
            No experiments yet. Train your first model above.
          </div>
        ) : (
          experiments.map(exp => <ExperimentDetail key={exp.id} experiment={exp} />)
        )}
      </div>
    </div>
  );
}
