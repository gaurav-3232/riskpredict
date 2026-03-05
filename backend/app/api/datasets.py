from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import DatasetResponse, DatasetListResponse
from app.services.services import DatasetService

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        dataset = DatasetService.save_upload(db, file.filename, content)
        return dataset
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=DatasetListResponse)
def list_datasets(db: Session = Depends(get_db)):
    datasets = DatasetService.get_all(db)
    return DatasetListResponse(datasets=datasets, total=len(datasets))


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = DatasetService.get_by_id(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset
