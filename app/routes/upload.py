# app/routes/upload.py
from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import shutil
import os

from app.database import SessionLocal
from app.models import Video
from app.utils.storage import upload_to_s3

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Uploads video → saves to DB → pushes to S3"""
    try:
        local_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(local_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        s3_key = f"videos/{file.filename}"
        s3_url = upload_to_s3(local_path, s3_key)

        video = Video(
            filename=file.filename,
            path=s3_url,
            is_processed=False,
            created_at=datetime.utcnow()
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        return {
            "status": "success",
            "video_id": video.id,
            "filename": file.filename,
            "s3_url": s3_url
        }

    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)
