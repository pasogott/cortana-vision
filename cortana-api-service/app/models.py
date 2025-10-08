from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

# Generate UUID for the primary key in the Video model
def generate_uuid():
    return str(uuid.uuid4())

class Video(Base):
    __tablename__ = 'videos'

    # Use String to store UUID values
    id = Column(String, primary_key=True, index=True, default=generate_uuid)  # UUID as String
    filename = Column(String, index=True)
    path = Column(String)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_processed_datetime_utc = Column(DateTime, nullable=True)

    frames = relationship("Frame", back_populates="video")

class Frame(Base):
    __tablename__ = 'frames'

    id = Column(String, primary_key=True, index=True, default=generate_uuid)  # UUID as String
    video_id = Column(String, ForeignKey('videos.id'))  # ForeignKey should also be String
    frame_number = Column(Integer)
    frame_time = Column(Float)  # Time in seconds for this frame
    path = Column(String)
    greyscale_is_processed = Column(Boolean, default=False)
    ocr_content = Column(String, nullable=True)

    video = relationship("Video", back_populates="frames")
