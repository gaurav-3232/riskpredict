from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import (
    TrainRequest,
    ExperimentResponse,
    ExperimentListResponse,
)
from app.services.services import ExperimentService

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("/train", response_model=ExperimentResponse)
def train_model(request: TrainRequest, db: Session = Depends(get_db)):
    try:
        experiment = ExperimentService.train_model(
            db=db,
            dataset_id=request.dataset_id,
            model_type=request.model_type,
            target_column=request.target_column,
            test_size=request.test_size,
        )
        return experiment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ExperimentListResponse)
def list_experiments(db: Session = Depends(get_db)):
    experiments = ExperimentService.get_all(db)
    return ExperimentListResponse(experiments=experiments, total=len(experiments))


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    experiment = ExperimentService.get_by_id(db, experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment
