import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

export interface Dataset {
  id: number;
  name: string;
  file_path: string;
  num_rows: number | null;
  num_columns: number | null;
  columns_info: Record<string, { dtype: string; nulls: number; unique: number }> | null;
  created_at: string;
}

export interface Experiment {
  id: number;
  dataset_id: number;
  model_type: string;
  target_column: string;
  test_size: number;
  metrics_json: {
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
    roc_auc: number;
    roc_curve?: { fpr: number[]; tpr: number[] };
    confusion_matrix: { matrix: number[][]; labels: string[] };
    feature_importance?: Record<string, number>;
  } | null;
  model_path: string | null;
  feature_columns: string[] | null;
  feature_stats: Record<string, { min: number; max: number; mean: number; is_categorical?: boolean; categories?: Record<string, number> }> | null;
  status: string;
  created_at: string;
}

export interface PredictionResult {
  id: number;
  experiment_id: number;
  input_json: Record<string, unknown>;
  prediction: string;
  probability: number;
  created_at: string;
}

// Datasets
export const uploadDataset = async (file: File): Promise<Dataset> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/datasets/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const getDatasets = async (): Promise<{ datasets: Dataset[]; total: number }> => {
  const { data } = await api.get('/datasets');
  return data;
};

export const getDataset = async (id: number): Promise<Dataset> => {
  const { data } = await api.get(`/datasets/${id}`);
  return data;
};

// Experiments
export const trainModel = async (params: {
  dataset_id: number;
  model_type: string;
  target_column: string;
  test_size: number;
}): Promise<Experiment> => {
  const { data } = await api.post('/experiments/train', params);
  return data;
};

export const getExperiments = async (): Promise<{ experiments: Experiment[]; total: number }> => {
  const { data } = await api.get('/experiments');
  return data;
};

export const getExperiment = async (id: number): Promise<Experiment> => {
  const { data } = await api.get(`/experiments/${id}`);
  return data;
};

// Predictions
export const makePrediction = async (params: {
  experiment_id: number;
  features: Record<string, number>;
}): Promise<PredictionResult> => {
  const { data } = await api.post('/predict', params);
  return data;
};

// Health
export const getHealth = async () => {
  const { data } = await api.get('/health');
  return data;
};

export default api;
