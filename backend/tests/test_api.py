import pytest
import tempfile
import os
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db

# Use SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test.db"):
        os.unlink("./test.db")


@pytest.fixture
def sample_csv_file():
    df = pd.DataFrame({
        "age": np.random.randint(20, 70, 100),
        "income": np.random.randint(20000, 100000, 100),
        "score": np.random.randn(100),
        "risk": np.random.choice([0, 1], 100),
    })
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        df.to_csv(f, index=False)
        return f.name


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]


def test_upload_dataset(sample_csv_file):
    with open(sample_csv_file, "rb") as f:
        response = client.post(
            "/datasets/upload",
            files={"file": ("test.csv", f, "text/csv")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test.csv"
    assert data["num_rows"] == 100
    os.unlink(sample_csv_file)


def test_list_datasets(sample_csv_file):
    with open(sample_csv_file, "rb") as f:
        client.post("/datasets/upload", files={"file": ("test.csv", f, "text/csv")})

    response = client.get("/datasets")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    os.unlink(sample_csv_file)


def test_train_experiment(sample_csv_file):
    with open(sample_csv_file, "rb") as f:
        upload = client.post("/datasets/upload", files={"file": ("test.csv", f, "text/csv")})
    dataset_id = upload.json()["id"]

    response = client.post("/experiments/train", json={
        "dataset_id": dataset_id,
        "model_type": "random_forest",
        "target_column": "risk",
        "test_size": 0.2,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["metrics_json"]["accuracy"] >= 0
    os.unlink(sample_csv_file)


def test_predict(sample_csv_file):
    with open(sample_csv_file, "rb") as f:
        upload = client.post("/datasets/upload", files={"file": ("test.csv", f, "text/csv")})
    dataset_id = upload.json()["id"]

    train_resp = client.post("/experiments/train", json={
        "dataset_id": dataset_id,
        "model_type": "logistic_regression",
        "target_column": "risk",
        "test_size": 0.2,
    })
    experiment_id = train_resp.json()["id"]

    response = client.post("/predict", json={
        "experiment_id": experiment_id,
        "features": {"age": 35, "income": 50000, "score": 0.5},
    })
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "probability" in data
    os.unlink(sample_csv_file)
