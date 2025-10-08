from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Snapshot Sandbox – Eagle Vision"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///snapshot.db"

    S3_URL: str
    S3_BUCKET: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    REGION: str
    STORAGE_PROVIDER: str

    UPLOAD_DIR: Path = Path("uploads")
    KEYFRAME_DIR: Path = Path("keyframes")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
