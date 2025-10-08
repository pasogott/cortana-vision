from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class OCRIndex(Base):
    __tablename__ = "ocr_index"

    id = Column(Integer, primary_key=True)
    video_id = Column(String, index=True)
    frame_path = Column(String)
    text = Column(Text)
