from fastapi import APIRouter, UploadFile, File, HTTPException
from app.utils.storage import save_upload, upload_to_s3   # ✅ include upload_to_s3
from app.utils.queue import publish_job
from app.database import SessionLocal
from app.models import Video
import os, uuid

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload video → Save locally → Upload to S3 → Create DB entry → Publish Redis job.
    """
    db = SessionLocal()
    try:
        # 1️⃣ Save video locally first
        file_path = save_upload(file)
        size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)

        # 2️⃣ Upload to S3 (Hetzner) and get remote URL
        video_id = str(uuid.uuid4())
        s3_key = f"videos/{video_id}/{file.filename}"
        s3_url = upload_to_s3(file_path, s3_key)   # ✅ use same helper as sampler

        # 3️⃣ Create DB row with S3 path (not local path)
        video = Video(
            id=video_id,
            filename=file.filename,
            path=s3_url,        # ✅ sampler will find this URL
        )
        db.add(video)
        db.commit()
        db.refresh(video)

        # 4️⃣ Publish Redis job for sampler (matching its event name)
        payload = {
            "video_id": video_id,
            "filename": file.filename,
            "s3_key": s3_key,  # optional, helps sampler directly
        }
        publish_job("make-samples-from-video", payload)

        # 5️⃣ Return response
        return {
            "status": "success",
            "message": "File uploaded, stored on S3, and sampler job queued",
            "video": {
                "id": video_id,
                "filename": file.filename,
                "path": s3_url,
                "size_mb": size_mb,
            },
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
