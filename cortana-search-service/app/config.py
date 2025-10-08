import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Core service info
    app_name: str = "Cortana Search Service"

    # Database / Redis / Temp
    database_url: str = os.getenv("DATABASE_URL", "sqlite:////app/data/snapshot.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://cortana-redis:6379/0")
    tmp_dir: str = os.getenv("TMP_DIR", "/app/tmp")

    # S3 configuration
    s3_url: str = os.getenv("S3_URL", "https://s3.amazonaws.com")
    s3_bucket: str = os.getenv("S3_BUCKET", "your-bucket-name")

    # Let unknown vars (like future ones) pass without raising ValidationError
    model_config = SettingsConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")

settings = Settings()
