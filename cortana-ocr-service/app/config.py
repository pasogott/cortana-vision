import os

class Settings:
    app_name = "Cortana OCR Worker"
    redis_url = os.getenv("REDIS_URL", "redis://cortana-redis:6379/0")
    jobs_channel = os.getenv("JOBS_CHANNEL", "cortana-jobs")
    event_ocr = os.getenv("EVENT_OCR", "run-ocr-from-greyscaled-samples")
    s3_url = os.getenv("S3_URL")
    s3_bucket = os.getenv("S3_BUCKET")
    s3_access_key = os.getenv("S3_ACCESS_KEY")
    s3_secret_key = os.getenv("S3_SECRET_KEY")
    region = os.getenv("REGION")
    tmp_dir = os.getenv("TMP_DIR", "/app/tmp")
    database_url = os.getenv("DATABASE_URL", "sqlite:////app/data/snapshot.db")

settings = Settings()
