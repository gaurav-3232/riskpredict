from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    num_rows = Column(Integer)
    num_columns = Column(Integer)
    columns_info = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    experiments = relationship("Experiment", back_populates="dataset")


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    model_type = Column(String(100), nullable=False)
    target_column = Column(String(255), nullable=False)
    test_size = Column(Float, default=0.2)
    metrics_json = Column(JSON)
    model_path = Column(String(500))
    feature_columns = Column(JSON)
    feature_stats = Column(JSON)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    dataset = relationship("Dataset", back_populates="experiments")
    predictions = relationship("Prediction", back_populates="experiment")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    input_json = Column(JSON, nullable=False)
    prediction = Column(String(255))
    probability = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    experiment = relationship("Experiment", back_populates="predictions")
