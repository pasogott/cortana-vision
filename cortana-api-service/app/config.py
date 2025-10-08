from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Cortana API Service"

    # --- Redis ---
    REDIS_URL: str = "redis://redis:6379/0"

    # --- Local storage ---
    STORAGE_BACKEND: str = "local"
    STORAGE_BUCKET: str = "cortana-videos"
    UPLOAD_DIR: str = "uploads"

    # --- S3 / Hetzner Object Storage ---
    S3_URL: str = ""
    S3_BUCKET: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    REGION: str = ""
    TMP_DIR: str = "/app/tmp"

    class Config:
        env_file = ".env"


settings = Settings()
