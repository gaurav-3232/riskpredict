import pytest
import os
import tempfile
import pandas as pd
import numpy as np
from app.ml.pipeline import MLPipeline


@pytest.fixture
def sample_csv():
    df = pd.DataFrame({
        "feature1": np.random.randn(200),
        "feature2": np.random.randn(200),
        "feature3": np.random.randn(200),
        "target": np.random.choice(["high_risk", "low_risk"], 200),
    })
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        df.to_csv(f, index=False)
        return f.name


@pytest.fixture
def pipeline():
    return MLPipeline()


def test_load_data(pipeline, sample_csv):
    df = pipeline.load_data(sample_csv)
    assert len(df) == 200
    assert "target" in df.columns
    os.unlink(sample_csv)


def test_prepare_data(pipeline, sample_csv):
    df = pipeline.load_data(sample_csv)
    X_train, X_test, y_train, y_test = pipeline.prepare_data(df, "target", 0.2)
    assert len(X_train) == 160
    assert len(X_test) == 40
    assert len(pipeline.feature_columns) == 3
    os.unlink(sample_csv)


@pytest.mark.parametrize("model_type", [
    "logistic_regression", "random_forest", "gradient_boosting"
])
def test_train_and_evaluate(pipeline, sample_csv, model_type):
    df = pipeline.load_data(sample_csv)
    X_train, X_test, y_train, y_test = pipeline.prepare_data(df, "target", 0.2)
    pipeline.train(model_type, X_train, y_train)
    metrics = pipeline.evaluate(X_test, y_test)

    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert "roc_auc" in metrics
    assert "confusion_matrix" in metrics
    assert 0.0 <= metrics["accuracy"] <= 1.0
    os.unlink(sample_csv)


def test_save_and_load_model(pipeline, sample_csv):
    df = pipeline.load_data(sample_csv)
    X_train, X_test, y_train, y_test = pipeline.prepare_data(df, "target", 0.2)
    pipeline.train("random_forest", X_train, y_train)

    with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
        model_path = f.name

    pipeline.save_model(model_path)
    artifact = MLPipeline.load_model(model_path)

    assert "model" in artifact
    assert "scaler" in artifact
    assert "feature_columns" in artifact
    os.unlink(model_path)
    os.unlink(sample_csv)


def test_predict_single(pipeline, sample_csv):
    df = pipeline.load_data(sample_csv)
    X_train, X_test, y_train, y_test = pipeline.prepare_data(df, "target", 0.2)
    pipeline.train("logistic_regression", X_train, y_train)

    with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
        model_path = f.name
    pipeline.save_model(model_path)

    artifact = MLPipeline.load_model(model_path)
    features = {"feature1": 0.5, "feature2": -0.3, "feature3": 1.2}
    pred, prob = MLPipeline.predict_single(artifact, features)

    assert pred in ["high_risk", "low_risk"]
    assert 0.0 <= prob <= 1.0
    os.unlink(model_path)
    os.unlink(sample_csv)
