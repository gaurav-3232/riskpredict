from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import PredictRequest, PredictResponse
from app.services.services import PredictionService

router = APIRouter(prefix="/predict", tags=["predictions"])


@router.post("", response_model=PredictResponse)
def make_prediction(request: PredictRequest, db: Session = Depends(get_db)):
    try:
        prediction = PredictionService.predict(
            db=db,
            experiment_id=request.experiment_id,
            features=request.features,
        )
        return prediction
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
