import pandas as pd
import numpy as np
import joblib
import json
import os
from typing import Optional
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix, roc_curve
)
from sklearn.pipeline import Pipeline
from app.core.logging import get_logger

logger = get_logger(__name__)

MODEL_REGISTRY = {
    "logistic_regression": LogisticRegression,
    "random_forest": RandomForestClassifier,
    "gradient_boosting": GradientBoostingClassifier,
}

MODEL_PARAMS = {
    "logistic_regression": {"max_iter": 1000, "random_state": 42},
    "random_forest": {"n_estimators": 100, "max_depth": 10, "random_state": 42},
    "gradient_boosting": {"n_estimators": 100, "max_depth": 5, "random_state": 42},
}


class MLPipeline:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy="median")
        self.label_encoder = LabelEncoder()
        self.feature_columns: list[str] = []
        self.feature_stats: dict = {}
        self.category_mappings: dict = {}
        self.target_column: str = ""

    def load_data(self, file_path: str) -> pd.DataFrame:
        logger.info("loading_data", file_path=file_path)
        df = pd.read_csv(file_path, encoding_errors="replace")
        # Clean column names: strip whitespace and carriage returns
        df.columns = df.columns.str.strip().str.replace("\r", "")
        logger.info("data_loaded", rows=len(df), columns=len(df.columns))
        return df

    def prepare_data(
        self, df: pd.DataFrame, target_column: str, test_size: float = 0.2
    ):
        self.target_column = target_column

        # Strip column name to match cleaned columns
        target_column = target_column.strip()
        self.target_column = target_column

        if target_column not in df.columns:
            raise ValueError(f"Target column '{target_column}' not found in dataset. Available: {list(df.columns)}")

        y = df[target_column].copy()
        X = df.drop(columns=[target_column])

        # Validate target is suitable for classification
        n_unique = y.nunique()
        if n_unique > 50:
            raise ValueError(
                f"Target column '{target_column}' has {n_unique} unique values. "
                f"Classification requires a categorical target (ideally ≤20 classes). "
                f"For this dataset, try 'Loan Default Risk' as the target column."
            )
        if n_unique < 2:
            raise ValueError(
                f"Target column '{target_column}' has only {n_unique} unique value(s). "
                f"Need at least 2 classes for classification."
            )

        # Keep only numeric columns
        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()

        # Encode non-numeric columns with few unique values and store the mappings
        self.category_mappings = {}
        all_cols = X.columns.tolist()
        cat_cols = [c for c in all_cols if c not in numeric_cols]
        for col in cat_cols:
            if X[col].nunique() <= 20:
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))
                # Store mapping: {label_string: encoded_int}
                self.category_mappings[col] = {
                    str(label): int(idx) for idx, label in enumerate(le.classes_)
                }
                numeric_cols.append(col)

        X = X[numeric_cols]
        self.feature_columns = numeric_cols

        # Compute feature stats BEFORE imputing/scaling (raw data ranges)
        self.feature_stats = {}
        for col in numeric_cols:
            stats: dict = {
                "min": round(float(X[col].min()), 2),
                "max": round(float(X[col].max()), 2),
                "mean": round(float(X[col].mean()), 2),
            }
            # Attach category options if this was a categorical column
            if col in self.category_mappings:
                stats["categories"] = self.category_mappings[col]
                stats["is_categorical"] = True
            self.feature_stats[col] = stats

        # Handle missing values
        X_imputed = pd.DataFrame(
            self.imputer.fit_transform(X), columns=X.columns, index=X.index
        )

        # Scale features
        X_scaled = pd.DataFrame(
            self.scaler.fit_transform(X_imputed), columns=X.columns, index=X.index
        )

        # Encode target if it's categorical
        if y.dtype == "object":
            y = self.label_encoder.fit_transform(y)
        else:
            # Convert to int for classification if values look like class labels
            if np.all(y == y.astype(int)):
                y = y.astype(int)
            self.label_encoder.classes_ = np.array(sorted(y.unique()))

        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=42, stratify=y
        )

        logger.info(
            "data_prepared",
            features=len(self.feature_columns),
            train_size=len(X_train),
            test_size=len(X_test),
        )

        return X_train, X_test, y_train, y_test

    def train(self, model_type: str, X_train, y_train):
        if model_type not in MODEL_REGISTRY:
            raise ValueError(f"Unknown model type: {model_type}")

        ModelClass = MODEL_REGISTRY[model_type]
        params = MODEL_PARAMS[model_type]
        self.model = ModelClass(**params)

        logger.info("training_model", model_type=model_type)
        self.model.fit(X_train, y_train)
        logger.info("training_complete", model_type=model_type)

        return self.model

    def evaluate(self, X_test, y_test) -> dict:
        if self.model is None:
            raise ValueError("Model not trained")

        y_pred = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)

        n_classes = len(self.label_encoder.classes_)
        avg = "binary" if n_classes == 2 else "weighted"

        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, average=avg, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, average=avg, zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, average=avg, zero_division=0)),
        }

        # ROC AUC
        try:
            if n_classes == 2:
                metrics["roc_auc"] = float(roc_auc_score(y_test, y_proba[:, 1]))
                fpr, tpr, _ = roc_curve(y_test, y_proba[:, 1])
                metrics["roc_curve"] = {
                    "fpr": [float(x) for x in fpr],
                    "tpr": [float(x) for x in tpr],
                }
            else:
                metrics["roc_auc"] = float(
                    roc_auc_score(y_test, y_proba, multi_class="ovr", average="weighted")
                )
        except Exception:
            metrics["roc_auc"] = 0.0

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        labels = [str(c) for c in self.label_encoder.classes_]
        metrics["confusion_matrix"] = {
            "matrix": cm.tolist(),
            "labels": labels,
        }

        # Feature importance (if available)
        if hasattr(self.model, "feature_importances_"):
            importance = self.model.feature_importances_
            metrics["feature_importance"] = dict(
                zip(self.feature_columns, [float(x) for x in importance])
            )
        elif hasattr(self.model, "coef_"):
            coef = np.abs(self.model.coef_).mean(axis=0) if self.model.coef_.ndim > 1 else np.abs(self.model.coef_[0])
            metrics["feature_importance"] = dict(
                zip(self.feature_columns, [float(x) for x in coef])
            )

        logger.info("evaluation_complete", accuracy=metrics["accuracy"], f1=metrics["f1_score"])
        return metrics

    def save_model(self, model_path: str):
        artifact = {
            "model": self.model,
            "scaler": self.scaler,
            "imputer": self.imputer,
            "label_encoder": self.label_encoder,
            "feature_columns": self.feature_columns,
            "target_column": self.target_column,
        }
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(artifact, model_path)
        logger.info("model_saved", path=model_path)

    @staticmethod
    def load_model(model_path: str) -> dict:
        artifact = joblib.load(model_path)
        logger.info("model_loaded", path=model_path)
        return artifact

    @staticmethod
    def predict_single(artifact: dict, features: dict) -> tuple[str, float]:
        model = artifact["model"]
        scaler = artifact["scaler"]
        imputer = artifact["imputer"]
        label_encoder = artifact["label_encoder"]
        feature_columns = artifact["feature_columns"]

        # Build feature vector in correct order
        feature_values = []
        for col in feature_columns:
            val = features.get(col, np.nan)
            try:
                val = float(val)
            except (ValueError, TypeError):
                val = np.nan
            feature_values.append(val)

        X = np.array([feature_values])
        X = imputer.transform(X)
        X = scaler.transform(X)

        prediction = model.predict(X)[0]
        proba = model.predict_proba(X)[0]
        max_proba = float(np.max(proba))

        pred_label = str(label_encoder.inverse_transform([prediction])[0])

        return pred_label, max_proba
