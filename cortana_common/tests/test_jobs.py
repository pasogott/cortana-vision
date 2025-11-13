"""Tests for job queue helpers."""

from uuid import uuid4

import pytest

from cortana_common.jobs import calculate_retry_delay
from cortana_common.models import JobType


def test_calculate_retry_delay():
    """Test retry delay calculation with exponential backoff."""
    delay0 = calculate_retry_delay(0)
    assert 48 <= delay0 <= 72  # 60 * 0.8 to 60 * 1.2
    
    delay1 = calculate_retry_delay(1)
    assert 144 <= delay1 <= 216  # 180 * 0.8 to 180 * 1.2
    
    delay2 = calculate_retry_delay(2)
    assert 432 <= delay2 <= 648  # 540 * 0.8 to 540 * 1.2
    
    assert delay1 > delay0
    assert delay2 > delay1


def test_job_type_values():
    """Test that JobType enum has correct values."""
    assert JobType.TRANSCODE.value == "transcode"
    assert JobType.SAMPLE.value == "sample"
    assert JobType.OCR.value == "ocr"
    assert JobType.SEGMENT_INDEX.value == "segment_index"
    assert JobType.CLIP_GENERATE.value == "clip_generate"
