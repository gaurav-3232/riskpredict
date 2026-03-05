from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import datasets, experiments, predictions, health
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import RequestLoggingMiddleware

settings = get_settings()
setup_logging()

app = FastAPI(
    title="RiskPredict API",
    description="Machine Learning Risk Prediction Platform",
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# Request logging
app.add_middleware(RequestLoggingMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(datasets.router)
app.include_router(experiments.router)
app.include_router(predictions.router)
