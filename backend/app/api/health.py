import time
import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.db.database import get_db
from app.models.models import Dataset, Experiment, Prediction
from app.core.config import get_settings

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    settings = get_settings()
    db_status = "healthy"
    db_latency_ms = 0.0
    try:
        start = time.perf_counter()
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - start) * 1000, 2)
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "version": "1.0.0",
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - _start_time),
        "database": {
            "status": db_status,
            "latency_ms": db_latency_ms,
        },
    }


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    return {
        "datasets_count": db.query(func.count(Dataset.id)).scalar(),
        "experiments_count": db.query(func.count(Experiment.id)).scalar(),
        "experiments_completed": db.query(func.count(Experiment.id)).filter(Experiment.status == "completed").scalar(),
        "predictions_count": db.query(func.count(Prediction.id)).scalar(),
        "uptime_seconds": round(time.time() - _start_time),
        "storage": {
            "models_dir": os.path.exists(get_settings().models_dir),
            "datasets_dir": os.path.exists(get_settings().datasets_dir),
        },
    }
