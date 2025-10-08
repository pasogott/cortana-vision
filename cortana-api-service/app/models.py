from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


# -------------------------------------------------
# Utility
# -------------------------------------------------
def generate_uuid() -> str:
    """Generate a UUID string for primary keys."""
    return str(uuid.uuid4())


# -------------------------------------------------
# Video Model
# -------------------------------------------------
class Video(Base):
    __tablename__ = "videos"

    # UUID as string PK
    id = Column(String, primary_key=True, index=True, default=generate_uuid)

    # Metadata
    filename = Column(String, index=True, nullable=False)
    path = Column(String, nullable=False)  # e.g., S3 or local path
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_processed_datetime_utc = Column(DateTime, nullable=True)

    # Relationship to frames
    frames = relationship("Frame", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video(id={self.id}, filename={self.filename})>"


# -------------------------------------------------
# Frame Model
# -------------------------------------------------
class Frame(Base):
    __tablename__ = "frames"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    frame_number = Column(Integer, nullable=False)
    frame_time = Column(Float, nullable=False)
    path = Column(String, nullable=False)
    greyscale_is_processed = Column(Boolean, default=False)
    ocr_content = Column(String, nullable=True)

    video = relationship("Video", back_populates="frames")

    def __repr__(self):
        return f"<Frame(id={self.id}, video_id={self.video_id}, frame_number={self.frame_number})>"
