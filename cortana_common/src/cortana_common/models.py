"""Pydantic models for cortana-vision database entities."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobType(str, Enum):
    """Job types matching database enum."""

    TRANSCODE = "transcode"
    SAMPLE = "sample"
    OCR = "ocr"
    SEGMENT_INDEX = "segment_index"
    CLIP_GENERATE = "clip_generate"


class JobStatus(str, Enum):
    """Job status matching database enum."""

    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class VideoStatus(str, Enum):
    """Video status matching database enum."""

    NEW = "new"
    PROCESSING = "processing"
    READY = "ready"


class Job(BaseModel):
    """Job model matching database schema."""

    id: UUID
    video_id: UUID
    job_type: JobType
    status: JobStatus
    retry_count: int = 0
    payload: Optional[dict[str, Any]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Video(BaseModel):
    """Video model matching database schema."""

    id: UUID
    owner_id: UUID
    team_id: Optional[UUID] = None
    platform: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None
    duration: Optional[int] = None  # in seconds
    s3_original_path: str
    s3_proxy_path: Optional[str] = None
    s3_thumb_path: Optional[str] = None
    status: VideoStatus = VideoStatus.NEW
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Segment(BaseModel):
    """Segment model matching database schema."""

    id: UUID
    video_id: UUID
    owner_id: UUID
    team_id: Optional[UUID] = None
    text: str
    normalized_text: str
    text_hash: str
    language: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    t_start: int  # milliseconds
    t_end: int  # milliseconds
    bounding_box: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
