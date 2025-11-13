"""Configuration management using pydantic-settings."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_role_key: str = Field(
        ..., description="Supabase service role key for bypassing RLS"
    )
    database_url: Optional[PostgresDsn] = Field(
        None, description="Direct PostgreSQL connection URL (optional)"
    )

    s3_endpoint: str = Field(..., description="S3-compatible endpoint URL")
    s3_bucket: str = Field(..., description="S3 bucket name")
    s3_access_key_id: str = Field(..., description="S3 access key ID")
    s3_secret_access_key: str = Field(..., description="S3 secret access key")
    s3_region: str = Field(default="us-east-1", description="S3 region")

    job_poll_interval: int = Field(
        default=5, description="Job polling interval in seconds"
    )
    job_max_retries: int = Field(default=3, description="Maximum job retry attempts")
    job_retry_base_delay: int = Field(
        default=60, description="Base delay for job retries in seconds"
    )

    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="json", description="Log format: json or text"
    )

    service_name: Optional[str] = Field(
        None, description="Name of the service (e.g., transcode-worker)"
    )
    worker_id: Optional[str] = Field(
        None, description="Unique worker ID for job leasing"
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Returns:
        Settings: Cached settings object loaded from environment.
    """
    return Settings()
