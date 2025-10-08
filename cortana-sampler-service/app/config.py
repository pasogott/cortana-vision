# app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")

    jobs_channel: str = Field("cortana-jobs", alias="JOBS_CHANNEL")
    event_samples: str = Field("make-samples-from-video", alias="EVENT_SAMPLES")
    event_greyscale: str = Field("make-greyscale-from-samples", alias="EVENT_GREYSCALE")

    s3_url: str = Field(..., alias="S3_URL")
    s3_bucket: str = Field(..., alias="S3_BUCKET")
    s3_access_key: str = Field(..., alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(..., alias="S3_SECRET_KEY")
    region: str = Field("nbg1", alias="REGION")

    sample_threshold: float = Field(0.08, alias="SAMPLE_THRESHOLD")
    tmp_dir: str = Field("/app/tmp", alias="TMP_DIR")

    # ✅ Add this line
    storage_provider: str = Field("hetzner", alias="STORAGE_PROVIDER")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }

settings = Settings()
