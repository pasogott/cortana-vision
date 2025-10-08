from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Video(Base):
    __tablename__ = "videos"
    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String)
    path = Column(String)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_processed_datetime_utc = Column(DateTime, nullable=True)
    frames = relationship("Frame", back_populates="video")

class Frame(Base):
    __tablename__ = "frames"
    id = Column(String, primary_key=True, default=generate_uuid)
    video_id = Column(String, ForeignKey("videos.id"))
    frame_number = Column(Integer)
    frame_time = Column(Float)
    path = Column(String)
    greyscale_is_processed = Column(Boolean, default=False)
    ocr_content = Column(String, nullable=True)
    video = relationship("Video", back_populates="frames")
