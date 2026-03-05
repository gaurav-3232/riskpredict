from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


# Dataset schemas
class DatasetResponse(BaseModel):
    id: int
    name: str
    file_path: str
    num_rows: Optional[int] = None
    num_columns: Optional[int] = None
    columns_info: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DatasetListResponse(BaseModel):
    datasets: list[DatasetResponse]
    total: int


# Experiment schemas
class TrainRequest(BaseModel):
    dataset_id: int
    model_type: str = Field(..., pattern="^(logistic_regression|random_forest|gradient_boosting)$")
    target_column: str
    test_size: float = Field(default=0.2, ge=0.1, le=0.5)


class ExperimentResponse(BaseModel):
    id: int
    dataset_id: int
    model_type: str
    target_column: str
    test_size: float
    metrics_json: Optional[dict] = None
    model_path: Optional[str] = None
    feature_columns: Optional[list] = None
    feature_stats: Optional[dict] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ExperimentListResponse(BaseModel):
    experiments: list[ExperimentResponse]
    total: int


# Prediction schemas
class PredictRequest(BaseModel):
    experiment_id: int
    features: dict[str, Any]


class PredictResponse(BaseModel):
    id: int
    experiment_id: int
    input_json: dict
    prediction: str
    probability: float
    created_at: datetime

    class Config:
        from_attributes = True


# Health
class HealthResponse(BaseModel):
    status: str
    database: str
    version: str = "1.0.0"
