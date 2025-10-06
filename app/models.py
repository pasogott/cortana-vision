import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, unique=True, nullable=False)
    path = Column(String, nullable=False)
    is_processed = Column(Boolean, default=False)
    is_processed_datetime_utc = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    frames = relationship("Frame", back_populates="video")


class Frame(Base):
    __tablename__ = "frames"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    path = Column(String, nullable=False)
    greyscaled_path = Column(String, nullable=True)
    greyscale_is_processed = Column(Boolean, default=False)
    greyscale_is_processed_datetime_utc = Column(DateTime, nullable=True)
    ocr_content = Column(String, nullable=True)
    frame_number = Column(Float, nullable=False)
    frame_time = Column(Float, nullable=True)

    video = relationship("Video", back_populates="frames")
