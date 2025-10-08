import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "sqlite:////app/data/snapshot.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://cortana-redis:6379/0")
    jobs_channel: str = os.getenv("JOBS_CHANNEL", "cortana-jobs")
    event_greyscale: str = os.getenv("EVENT_GREYSCALE", "make-greyscale-from-samples")
    event_ocr: str = os.getenv("EVENT_OCR", "run-ocr-from-greyscaled-samples")
    s3_url: str = os.getenv("S3_URL")
    s3_bucket: str = os.getenv("S3_BUCKET")
    s3_access_key: str = os.getenv("S3_ACCESS_KEY")
    s3_secret_key: str = os.getenv("S3_SECRET_KEY")
    region: str = os.getenv("REGION")
    tmp_dir: str = os.getenv("TMP_DIR", "/app/tmp")

settings = Settings()
