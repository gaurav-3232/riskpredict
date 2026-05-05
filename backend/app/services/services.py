import os
import uuid
from functools import lru_cache
import pandas as pd
from sqlalchemy.orm import Session
from app.models.models import Dataset, Experiment, Prediction
from app.ml.pipeline import MLPipeline
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


# Cache loaded model artifacts in memory keyed by file path.
# Without this, every /predict call re-reads the model from disk via joblib,
# which is the dominant cost of the request and holds the DB connection open
# for hundreds of ms — the root cause of pool exhaustion under load.
@lru_cache(maxsize=32)
def _load_model_cached(model_path: str) -> dict:
    return MLPipeline.load_model(model_path)


class DatasetService:
    @staticmethod
    def save_upload(db: Session, filename: str, content: bytes) -> Dataset:
        os.makedirs(settings.datasets_dir, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(settings.datasets_dir, unique_name)
        with open(file_path, "wb") as f:
            f.write(content)

        df = pd.read_csv(file_path)
        dataset = Dataset(
            name=filename,
            file_path=file_path,
            num_rows=len(df),
            num_columns=len(df.columns),
            columns=list(df.columns),
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        logger.info("dataset_uploaded", id=dataset.id, name=filename, rows=len(df))
        return dataset


class ExperimentService:
    @staticmethod
    def get_all(db: Session):
        return (
            db.query(Experiment)
            .order_by(Experiment.id.desc())
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, experiment_id: int):
        return db.query(Experiment).filter(Experiment.id == experiment_id).first()
    @staticmethod
    def train_model(
        db: Session,
        dataset_id: int,
        model_type: str,
        target_column: str,
        test_size: float = 0.2,
    ) -> Experiment:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        experiment = Experiment(
            dataset_id=dataset_id,
            model_type=model_type,
            target_column=target_column,
            test_size=test_size,
            status="running",
        )
        db.add(experiment)
        db.commit()
        db.refresh(experiment)

        try:
            os.makedirs(settings.models_dir, exist_ok=True)
            model_path = os.path.join(
                settings.models_dir,
                f"model_{experiment.id}_{model_type}.joblib",
            )
            artifact, metrics = MLPipeline.train(
                file_path=dataset.file_path,
                target_column=target_column,
                model_type=model_type,
                test_size=test_size,
            )
            MLPipeline.save_model(artifact, model_path)

            experiment.model_path = model_path
            experiment.feature_columns = artifact["feature_columns"]
            experiment.metrics_json = metrics
            experiment.status = "completed"
            db.commit()
            db.refresh(experiment)
            logger.info("experiment_completed", id=experiment.id)
        except Exception as e:
            experiment.status = "failed"
            experiment.metrics_json = {"error": str(e)}
            db.commit()
            logger.error("experiment_failed", id=experiment.id, error=str(e))

        return experiment


class PredictionService:
    @staticmethod
    def predict(db: Session, experiment_id: int, features: dict) -> Prediction:
        experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        if experiment.status != "completed":
            raise ValueError(f"Experiment {experiment_id} is not completed")
        if not experiment.model_path:
            raise ValueError(f"Experiment {experiment_id} has no model path")

        # Use cached loader instead of MLPipeline.load_model() directly.
        # First call per model: ~700ms (disk I/O + joblib deserialization).
        # Subsequent calls: microseconds (in-memory hit).
        artifact = _load_model_cached(experiment.model_path)
        pred_label, probability = MLPipeline.predict_single(artifact, features)

        prediction = Prediction(
            experiment_id=experiment_id,
            input_json=features,
            prediction=str(pred_label),
            probability=float(probability),
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        return prediction