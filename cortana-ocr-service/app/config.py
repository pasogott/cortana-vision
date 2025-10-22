# cortana-ocr-service/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Core
    app_name: str = "Cortana OCR"
    database_url: str = "sqlite:////app/data/snapshot.db"
    redis_url: str = "redis://cortana-redis:6379/0"

    # Channels
    jobs_channel: str = "cortana-jobs"
    events_channel: str = "cortana-events"

    # Event names
    event_samples: str = "make-samples-from-video"
    event_greyscale: str = "make-greyscale-from-samples"
    event_ocr: str = "run-ocr-from-greyscaled-samples"
    event_ocr_update: str = "ocr-index-updated"

    # Object storage (Hetzner / S3 compatible)
    s3_url: str | None = None
    s3_bucket: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    region: str | None = None
    storage_provider: str | None = None

    # Misc
    tmp_dir: str = "/app/tmp"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
