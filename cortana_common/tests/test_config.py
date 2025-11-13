"""Tests for configuration management."""

import os
from unittest.mock import patch

import pytest

from cortana_common.config import Settings, get_settings


@pytest.fixture
def mock_env():
    """Mock environment variables for testing."""
    env_vars = {
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
        "S3_ENDPOINT": "https://test.s3.amazonaws.com",
        "S3_BUCKET": "test-bucket",
        "S3_ACCESS_KEY_ID": "test-access-key",
        "S3_SECRET_ACCESS_KEY": "test-secret-key",
        "S3_REGION": "us-east-1",
        "JOB_POLL_INTERVAL": "10",
        "JOB_MAX_RETRIES": "5",
        "LOG_LEVEL": "DEBUG",
    }
    
    with patch.dict(os.environ, env_vars, clear=True):
        get_settings.cache_clear()
        yield env_vars


def test_settings_from_env(mock_env):
    """Test that settings are loaded from environment variables."""
    settings = Settings()
    
    assert settings.supabase_url == "https://test-project.supabase.co"
    assert settings.supabase_service_role_key == "test-service-key"
    assert settings.s3_endpoint == "https://test.s3.amazonaws.com"
    assert settings.s3_bucket == "test-bucket"
    assert settings.s3_access_key_id == "test-access-key"
    assert settings.s3_secret_access_key == "test-secret-key"
    assert settings.s3_region == "us-east-1"
    assert settings.job_poll_interval == 10
    assert settings.job_max_retries == 5
    assert settings.log_level == "DEBUG"


def test_settings_defaults(mock_env):
    """Test that default values are applied."""
    settings = Settings()
    
    assert settings.s3_region == "us-east-1"
    assert settings.job_poll_interval == 10
    assert settings.log_format == "json"


def test_get_settings_cached(mock_env):
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2


def test_settings_validation_missing_required():
    """Test that validation fails for missing required fields."""
    with patch.dict(os.environ, {}, clear=True):
        get_settings.cache_clear()
        
        with pytest.raises(Exception):  # pydantic ValidationError
            Settings()
