import os
import uuid
import pandas as pd
from sqlalchemy.orm import Session
from app.models.models import Dataset, Experiment, Prediction
from app.ml.pipeline import MLPipeline
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class DatasetService:
    @staticmethod
    def save_upload(db: Session, filename: str, content: bytes) -> Dataset:
        os.makedirs(settings.datasets_dir, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(settings.datasets_dir, safe_name)

        with open(file_path, "wb") as f:
            f.write(content)

        df = pd.read_csv(file_path, encoding_errors="replace")
        df.columns = df.columns.str.strip().str.replace("\r", "")
        columns_info = {}
        for col in df.columns:
            columns_info[col] = {
                "dtype": str(df[col].dtype),
                "nulls": int(df[col].isnull().sum()),
                "unique": int(df[col].nunique()),
            }

        dataset = Dataset(
            name=filename,
            file_path=file_path,
            num_rows=len(df),
            num_columns=len(df.columns),
            columns_info=columns_info,
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        logger.info("dataset_uploaded", id=dataset.id, name=filename, rows=len(df))
        return dataset

    @staticmethod
    def get_all(db: Session) -> list[Dataset]:
        return db.query(Dataset).order_by(Dataset.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, dataset_id: int) -> Dataset | None:
        return db.query(Dataset).filter(Dataset.id == dataset_id).first()


class ExperimentService:
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
            status="training",
        )
        db.add(experiment)
        db.commit()
        db.refresh(experiment)

        try:
            pipeline = MLPipeline()
            df = pipeline.load_data(dataset.file_path)
            X_train, X_test, y_train, y_test = pipeline.prepare_data(
                df, target_column, test_size
            )
            pipeline.train(model_type, X_train, y_train)
            metrics = pipeline.evaluate(X_test, y_test)

            model_filename = f"model_{experiment.id}_{model_type}.joblib"
            model_path = os.path.join(settings.models_dir, model_filename)
            pipeline.save_model(model_path)

            experiment.metrics_json = metrics
            experiment.model_path = model_path
            experiment.feature_columns = pipeline.feature_columns
            experiment.feature_stats = pipeline.feature_stats
            experiment.status = "completed"

            logger.info(
                "experiment_completed",
                id=experiment.id,
                model=model_type,
                accuracy=metrics["accuracy"],
            )
        except Exception as e:
            experiment.status = "failed"
            experiment.metrics_json = {"error": str(e)}
            logger.error("experiment_failed", id=experiment.id, error=str(e))

        db.commit()
        db.refresh(experiment)
        return experiment

    @staticmethod
    def get_all(db: Session) -> list[Experiment]:
        return db.query(Experiment).order_by(Experiment.created_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, experiment_id: int) -> Experiment | None:
        return db.query(Experiment).filter(Experiment.id == experiment_id).first()


class PredictionService:
    @staticmethod
    def predict(
        db: Session, experiment_id: int, features: dict
    ) -> Prediction:
        experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        if experiment.status != "completed":
            raise ValueError(f"Experiment {experiment_id} is not completed")
        if not experiment.model_path:
            raise ValueError(f"No model found for experiment {experiment_id}")

        artifact = MLPipeline.load_model(experiment.model_path)
        pred_label, probability = MLPipeline.predict_single(artifact, features)

        prediction = Prediction(
            experiment_id=experiment_id,
            input_json=features,
            prediction=pred_label,
            probability=probability,
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)

        logger.info(
            "prediction_made",
            experiment_id=experiment_id,
            prediction=pred_label,
            probability=probability,
        )
        return prediction

    @staticmethod
    def get_by_experiment(db: Session, experiment_id: int) -> list[Prediction]:
        return (
            db.query(Prediction)
            .filter(Prediction.experiment_id == experiment_id)
            .order_by(Prediction.created_at.desc())
            .all()
        )
