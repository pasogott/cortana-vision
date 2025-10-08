from sqlalchemy import Column, Integer, String, Text, Boolean
from app.database import Base

class OCRFrame(Base):
    __tablename__ = "ocr_frames"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String, index=True)
    frame_path = Column(String)
    ocr_text = Column(Text)
    is_processed = Column(Boolean, default=False)
