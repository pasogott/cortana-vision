"""Tests for pydantic models."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cortana_common.models import (
    Job,
    JobStatus,
    JobType,
    Segment,
    Video,
    VideoStatus,
)


def test_job_model():
    """Test Job model creation and validation."""
    job_id = uuid4()
    video_id = uuid4()
    now = datetime.now(UTC)
    
    job = Job(
        id=job_id,
        video_id=video_id,
        job_type=JobType.TRANSCODE,
        status=JobStatus.QUEUED,
        retry_count=0,
        payload={"test": "data"},
        created_at=now,
        updated_at=now,
    )
    
    assert job.id == job_id
    assert job.video_id == video_id
    assert job.job_type == JobType.TRANSCODE
    assert job.status == JobStatus.QUEUED
    assert job.retry_count == 0
    assert job.payload == {"test": "data"}


def test_job_type_enum():
    """Test JobType enum values."""
    assert JobType.TRANSCODE.value == "transcode"
    assert JobType.SAMPLE.value == "sample"
    assert JobType.OCR.value == "ocr"
    assert JobType.SEGMENT_INDEX.value == "segment_index"
    assert JobType.CLIP_GENERATE.value == "clip_generate"


def test_job_status_enum():
    """Test JobStatus enum values."""
    assert JobStatus.QUEUED.value == "queued"
    assert JobStatus.PROCESSING.value == "processing"
    assert JobStatus.DONE.value == "done"
    assert JobStatus.FAILED.value == "failed"


def test_video_model():
    """Test Video model creation and validation."""
    video_id = uuid4()
    owner_id = uuid4()
    now = datetime.now(UTC)
    
    video = Video(
        id=video_id,
        owner_id=owner_id,
        platform="tiktok",
        resolution="1920x1080",
        fps=120,
        duration=300,
        s3_original_path="videos/original/test/master.mp4",
        s3_proxy_path="videos/proxy/test/index.m3u8",
        status=VideoStatus.READY,
        created_at=now,
        updated_at=now,
    )
    
    assert video.id == video_id
    assert video.owner_id == owner_id
    assert video.platform == "tiktok"
    assert video.fps == 120
    assert video.status == VideoStatus.READY


def test_video_status_enum():
    """Test VideoStatus enum values."""
    assert VideoStatus.NEW.value == "new"
    assert VideoStatus.PROCESSING.value == "processing"
    assert VideoStatus.READY.value == "ready"


def test_segment_model():
    """Test Segment model creation and validation."""
    segment_id = uuid4()
    video_id = uuid4()
    owner_id = uuid4()
    now = datetime.now(UTC)
    
    segment = Segment(
        id=segment_id,
        video_id=video_id,
        owner_id=owner_id,
        text="Hello World",
        normalized_text="hello world",
        text_hash="abc123",
        language="eng",
        confidence=0.95,
        t_start=1000,
        t_end=2000,
        bounding_box={"x": 100, "y": 200, "width": 300, "height": 50},
        created_at=now,
    )
    
    assert segment.id == segment_id
    assert segment.video_id == video_id
    assert segment.text == "Hello World"
    assert segment.confidence == 0.95
    assert segment.t_start == 1000
    assert segment.t_end == 2000


def test_segment_confidence_validation():
    """Test that segment confidence is validated to be between 0 and 1."""
    segment_id = uuid4()
    video_id = uuid4()
    owner_id = uuid4()
    now = datetime.now(UTC)
    
    segment = Segment(
        id=segment_id,
        video_id=video_id,
        owner_id=owner_id,
        text="Test",
        normalized_text="test",
        text_hash="hash",
        confidence=0.5,
        t_start=0,
        t_end=100,
        created_at=now,
    )
    assert segment.confidence == 0.5
    
    with pytest.raises(Exception):  # pydantic ValidationError
        Segment(
            id=segment_id,
            video_id=video_id,
            owner_id=owner_id,
            text="Test",
            normalized_text="test",
            text_hash="hash",
            confidence=1.5,
            t_start=0,
            t_end=100,
            created_at=now,
        )
    
    with pytest.raises(Exception):  # pydantic ValidationError
        Segment(
            id=segment_id,
            video_id=video_id,
            owner_id=owner_id,
            text="Test",
            normalized_text="test",
            text_hash="hash",
            confidence=-0.1,
            t_start=0,
            t_end=100,
            created_at=now,
        )
