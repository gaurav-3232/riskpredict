import { useState, useEffect } from 'react';
import { Crosshair, Sparkles, Info } from 'lucide-react';
import { getExperiments, makePrediction, type Experiment, type PredictionResult } from '../services/api';

export default function Predict() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExpId, setSelectedExpId] = useState<number | ''>('');
  const [features, setFeatures] = useState<Record<string, string>>({});
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<PredictionResult[]>([]);

  const completedExperiments = experiments.filter(e => e.status === 'completed');
  const selectedExp = completedExperiments.find(e => e.id === selectedExpId);

  useEffect(() => {
    getExperiments().then(res => setExperiments(res.experiments));
  }, []);

  useEffect(() => {
    if (selectedExp?.feature_columns) {
      const init: Record<string, string> = {};
      selectedExp.feature_columns.forEach(col => {
        const stats = selectedExp.feature_stats?.[col];
        if (stats?.is_categorical && stats?.categories) {
          // Default to first category option
          const firstVal = Object.values(stats.categories as Record<string, number>)[0];
          init[col] = String(firstVal ?? 0);
        } else {
          init[col] = stats ? String(stats.mean) : '';
        }
      });
      setFeatures(init);
      setResult(null);
    }
  }, [selectedExpId]);

  const handlePredict = async () => {
    if (!selectedExpId) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const numericFeatures: Record<string, number> = {};
      for (const [k, v] of Object.entries(features)) {
        numericFeatures[k] = parseFloat(v) || 0;
      }
      const res = await makePrediction({ experiment_id: selectedExpId as number, features: numericFeatures });
      setResult(res);
      setHistory(prev => [res, ...prev].slice(0, 20));
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Prediction failed');
    } finally {
      setLoading(false);
    }
  };

  const riskColor = (prediction: string) => {
    const lower = prediction.toLowerCase();
    if (lower.includes('high') || lower === '1' || lower === 'true' || lower === 'yes')
      return { bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/20', glow: 'shadow-red-500/10' };
    return { bg: 'bg-emerald-500/15', text: 'text-emerald-400', border: 'border-emerald-500/20', glow: 'shadow-emerald-500/10' };
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Predict</h1>
        <p className="text-slate-400 mt-1">Run predictions using trained models</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="glass-card p-6">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Select Model</h3>
            <select
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500"
              value={selectedExpId}
              onChange={e => setSelectedExpId(Number(e.target.value))}
            >
              <option value="">Select an experiment...</option>
              {completedExperiments.map(e => (
                <option key={e.id} value={e.id}>
                  #{e.id} — {e.model_type.replace(/_/g, ' ')} (Acc: {((e.metrics_json?.accuracy || 0) * 100).toFixed(1)}%)
                </option>
              ))}
            </select>
          </div>

          {selectedExp && selectedExp.feature_columns && (
            <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-slate-300">Input Features</h3>
                {selectedExp.feature_stats && (
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <Info size={12} />
                    Pre-filled with defaults from training data
                  </div>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {selectedExp.feature_columns.map(col => {
                  const stats = selectedExp.feature_stats?.[col];
                  const isCategorical = stats?.is_categorical && stats?.categories;

                  if (isCategorical) {
                    const categories = stats.categories as Record<string, number>;
                    return (
                      <div key={col}>
                        <label className="block text-xs text-slate-500 mb-1 font-mono">{col}</label>
                        <select
                          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500"
                          value={features[col] || ''}
                          onChange={e => setFeatures(prev => ({ ...prev, [col]: e.target.value }))}
                        >
                          {Object.entries(categories).map(([label, value]) => (
                            <option key={label} value={value}>{label}</option>
                          ))}
                        </select>
                        <p className="text-[10px] text-slate-600 mt-1">Categorical</p>
                      </div>
                    );
                  }

                  // Numeric input with range bar
                  const val = parseFloat(features[col]) || 0;
                  const inRange = stats ? (val >= stats.min && val <= stats.max) : true;
                  const pct = stats ? Math.max(0, Math.min(100, ((val - stats.min) / (stats.max - stats.min)) * 100)) : 0;

                  return (
                    <div key={col}>
                      <label className="block text-xs text-slate-500 mb-1 font-mono">{col}</label>
                      <input
                        type="number"
                        step="any"
                        className={`w-full bg-slate-800 border rounded-lg px-3 py-2 text-sm text-white focus:outline-none font-mono ${
                          !inRange && features[col] ? 'border-amber-500/50 focus:border-amber-500' : 'border-slate-700 focus:border-brand-500'
                        }`}
                        value={features[col] || ''}
                        onChange={e => setFeatures(prev => ({ ...prev, [col]: e.target.value }))}
                        placeholder={stats ? `${stats.mean}` : '0.0'}
                      />
                      {stats && (
                        <div className="flex items-center gap-2 mt-1.5">
                          <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden relative">
                            <div
                              className={`absolute top-0 left-0 h-full rounded-full transition-all ${inRange ? 'bg-brand-500' : 'bg-amber-500'}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="text-[10px] text-slate-600 font-mono whitespace-nowrap">
                            {stats.min} – {stats.max}
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {error && <p className="text-red-400 text-sm mt-3">{error}</p>}

              <button
                className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
                onClick={handlePredict}
                disabled={loading}
              >
                {loading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Crosshair size={16} />
                )}
                {loading ? 'Predicting...' : 'Run Prediction'}
              </button>
            </div>
          )}
        </div>

        <div className="space-y-4">
          {result && (() => {
            const colors = riskColor(result.prediction);
            return (
              <div className={`glass-card p-6 glow-sm ${colors.glow}`}>
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles size={16} className="text-brand-400" />
                  <h3 className="text-sm font-semibold text-slate-300">Prediction Result</h3>
                </div>
                <div className={`text-center py-6 rounded-lg ${colors.bg} border ${colors.border}`}>
                  <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Predicted Class</p>
                  <p className={`text-3xl font-bold ${colors.text}`}>{result.prediction}</p>
                  <p className="text-sm text-slate-400 mt-2">
                    Confidence: <span className="font-mono font-bold text-white">{(result.probability * 100).toFixed(2)}%</span>
                  </p>
                </div>
              </div>
            );
          })()}

          {history.length > 0 && (
            <div className="glass-card p-6">
              <h3 className="text-sm font-semibold text-slate-300 mb-3">Recent Predictions</h3>
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {history.map((h, i) => {
                  const colors = riskColor(h.prediction);
                  return (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-slate-800/50 last:border-0">
                      <span className={`text-sm font-medium ${colors.text}`}>{h.prediction}</span>
                      <span className="text-xs text-slate-500 font-mono">{(h.probability * 100).toFixed(1)}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {!selectedExpId && (
            <div className="glass-card p-8 text-center">
              <Crosshair size={32} className="text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-500">Select a trained model to start making predictions</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
