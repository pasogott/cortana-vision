from fastapi import APIRouter, UploadFile, File, HTTPException
from app.utils.storage import save_upload
from app.utils.queue import publish_job
from app.utils.s3 import upload_to_s3
from app.database import SessionLocal
from app.models import Video
import os, uuid, time

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/")
async def upload_video(file: UploadFile = File(...)):
    start_time = time.time()
    print("[UPLOAD] Starting upload process...")

    db = SessionLocal()
    try:
        # 1️⃣ Save video locally (temporary)
        print(f"[UPLOAD] Saving file: {file.filename}")
        local_path = save_upload(file)
        size_mb = round(os.path.getsize(local_path) / (1024 * 1024), 2)
        print(f"[UPLOAD] Saved locally: {local_path} ({size_mb} MB)")

        # 2️⃣ Generate UUID and S3 path
        video_id = str(uuid.uuid4())
        s3_key = f"videos/{video_id}/{file.filename}"

        # 3️⃣ Upload to S3
        print(f"[UPLOAD] Uploading to S3 as {s3_key}")
        s3_url = upload_to_s3(local_path, s3_key)
        print(f"[UPLOAD] Uploaded to S3 → {s3_url}")

        # 4️⃣ Create DB entry
        video = Video(
            id=video_id,
            filename=file.filename,
            path=s3_url,  # ✅ stored as S3 URL
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        print(f"[UPLOAD] DB entry created for {video_id}")

        # 5️⃣ Publish Redis job for sampler
        payload = {"video_id": video_id, "filename": file.filename}
        publish_job("make-samples-from-video", payload)
        print(f"[UPLOAD] Job published → {payload}")

        # 6️⃣ Cleanup (optional)
        try:
            os.remove(local_path)
            print("[UPLOAD] Temporary file removed.")
        except Exception as e:
            print(f"[UPLOAD] Cleanup warning: {e}")

        elapsed = round(time.time() - start_time, 2)
        print(f"[UPLOAD] Done in {elapsed}s")

        return {
            "status": "success",
            "message": "File uploaded, stored on S3, and sampler job queued",
            "video": {
                "id": video_id,
                "filename": file.filename,
                "s3_url": s3_url,
                "size_mb": size_mb,
                "elapsed_seconds": elapsed,
            },
        }

    except Exception as e:
        db.rollback()
        print(f"[UPLOAD][ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()
        print("[UPLOAD] DB session closed.")
