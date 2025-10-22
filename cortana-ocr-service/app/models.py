from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


# -------------------------------------------------
# Video Model
# -------------------------------------------------
class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    filename = Column(String, index=True, nullable=False)
    path = Column(String, nullable=True)  # e.g. S3 URL
    is_processed = Column(Boolean, default=False)
    status = Column(String, default="processing")  # added for OCR ready tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    is_processed_datetime_utc = Column(DateTime, nullable=True)

    frames = relationship("Frame", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video(id={self.id}, filename={self.filename}, status={self.status})>"


# -------------------------------------------------
# Frame Model
# -------------------------------------------------
class Frame(Base):
    __tablename__ = "frames"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    frame_number = Column(Integer, nullable=False)
    frame_time = Column(Float, nullable=False)
    path = Column(String, nullable=False)  # S3 or local path
    greyscale_is_processed = Column(Boolean, default=False)
    ocr_content = Column(Text, nullable=True)

    video = relationship("Video", back_populates="frames")

    def __repr__(self):
        return f"<Frame(id={self.id}, video_id={self.video_id}, frame_number={self.frame_number})>"


# -------------------------------------------------
# OCRFrame Model
# -------------------------------------------------
class OCRFrame(Base):
    __tablename__ = "ocr_frames"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String, index=True)
    frame_path = Column(String)
    ocr_text = Column(Text)
    is_processed = Column(Boolean, default=False)

    def __repr__(self):
        return f"<OCRFrame(video_id={self.video_id}, processed={self.is_processed})>"
