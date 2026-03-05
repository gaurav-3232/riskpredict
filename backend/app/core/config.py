from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from typing import Optional
import json


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://riskpredict:riskpredict_secret@localhost:5432/riskpredict"

    # Storage
    models_dir: str = "/app/storage/models"
    datasets_dir: str = "/app/storage/datasets"
    max_upload_size: int = 50 * 1024 * 1024  # 50MB

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # Logging
    log_level: str = "INFO"

    # Environment
    environment: str = "development"

    # Auth (reserved for future use)
    jwt_secret: Optional[str] = None

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
